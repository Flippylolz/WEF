"""Progress health uses identities and deadlines, never source silence or attempts."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from wef_backend.features.ingestion.domain.ingestion_progress import (
    AcceptanceSample,
    ProgressSnapshot,
    assess_acceptance,
    classify_progress,
)

NOW = datetime(2026, 9, 6, tzinfo=UTC)


def test_attempting_terminal_siblings_is_stalled_without_unique_progress() -> None:
    snapshot = ProgressSnapshot("archive", "terminal:1", eligible=25, attempted=100, oldest_due=NOW)
    state = None
    for minute in range(6):
        state = classify_progress(
            replace(snapshot, attempted=100 + minute * 25), state, NOW + timedelta(minutes=minute)
        )
    assert state is not None
    assert state.status == "stalled"
    assert state.reason == "eligible_without_unique_progress"
    state = classify_progress(
        replace(snapshot, token="terminal:2"), state, NOW + timedelta(minutes=6)
    )
    assert state is not None
    assert state.status == "progressing"
    assert state.healthy_samples == 1


@pytest.mark.parametrize(
    ("snapshot", "expected"),
    [
        (ProgressSnapshot("archive", "0"), "idle"),
        (ProgressSnapshot("archive", "0", delayed=2), "waiting"),
        (ProgressSnapshot("media", "0", eligible=10, leased=1), "in_flight"),
        (ProgressSnapshot("media", "0", eligible=10, paused=True), "paused"),
        (ProgressSnapshot("archive", "0", quarantined=20), "idle"),
    ],
)
def test_idle_waiting_and_leases_are_not_stalls(snapshot: ProgressSnapshot, expected: str) -> None:
    state = None
    for minute in range(20):
        state = classify_progress(snapshot, state, NOW + timedelta(minutes=minute))
    assert state is not None
    assert state.status == expected
    assert state.reason is None


def test_provider_floor_and_grace_prevent_false_stall() -> None:
    snapshot = ProgressSnapshot(
        "media", "0", eligible=2, oldest_due=NOW, wait_until=NOW + timedelta(minutes=10)
    )
    state = None
    for minute in range(13):
        state = classify_progress(snapshot, state, NOW + timedelta(minutes=minute))
    assert state is not None
    assert state.status == "waiting"
    state = classify_progress(snapshot, state, NOW + timedelta(minutes=13))
    assert state is not None
    assert state.status == "stalled"


def test_newly_eligible_record_is_not_old_backlog() -> None:
    state = None
    for minute in range(20):
        snapshot = ProgressSnapshot(
            "archive", "0", eligible=1, oldest_due=NOW + timedelta(minutes=minute)
        )
        state = classify_progress(snapshot, state, NOW + timedelta(minutes=minute))
    assert state is not None
    assert state.status == "progressing"


@pytest.mark.parametrize("offset", [-60, 0, 180])
def test_clock_regression_duplicate_and_gap_invalidate_comparison(offset: int) -> None:
    snapshot = ProgressSnapshot("archive", "0", eligible=2, oldest_due=NOW)
    previous = classify_progress(snapshot, None, NOW)
    result = classify_progress(snapshot, previous, NOW + timedelta(seconds=offset))
    assert result.status == "observing"
    assert result.healthy_samples == 0


def test_systemic_pause_is_actionable_but_operator_pause_is_not() -> None:
    snapshot = ProgressSnapshot("media", "0", paused=True, actionable_pause=True)
    previous = classify_progress(snapshot, None, NOW)
    result = classify_progress(snapshot, previous, NOW + timedelta(minutes=1))
    assert result.reason == "systemic_pause"


def test_population_reconciliation_does_not_sum_observations() -> None:
    snapshot = ProgressSnapshot(
        "media",
        "0",
        eligible=2,
        delayed=3,
        leased=1,
        terminal=7,
        quarantined=4,
        completed=5,
        attempted=500,
    )
    assert snapshot.total == 17


def test_acceptance_requires_a_full_contiguous_day() -> None:

    samples = [
        AcceptanceSample(NOW + timedelta(minutes=i), healthy=True, eligible=0, terminal_replays=0)
        for i in range(1441)
    ]
    assert assess_acceptance(samples[:-1], samples[-2].sampled_at)["status"] == "collecting"
    assert assess_acceptance(samples, samples[-1].sampled_at)["status"] == "passed"
    assert (
        assess_acceptance(samples, samples[-1].sampled_at + timedelta(minutes=3))["status"]
        == "sampling_gap"
    )
    samples[-1] = replace(samples[-1], terminal_replays=1)
    assert assess_acceptance(samples, samples[-1].sampled_at)["status"] == "collecting"


def test_acceptance_restarts_after_unhealthy_or_missing_samples() -> None:

    assert assess_acceptance([], NOW)["status"] == "collecting"
    bad = AcceptanceSample(NOW, healthy=False, eligible=0, terminal_replays=0)
    assert assess_acceptance([bad], NOW)["status"] == "unhealthy"
    first = replace(bad, healthy=True)
    later = replace(first, sampled_at=NOW + timedelta(minutes=3))
    assert assess_acceptance([first, later], later.sampled_at)["seconds"] == 0
    later = replace(first, sampled_at=NOW + timedelta(minutes=1), eligible=2)
    assert assess_acceptance([first, later], later.sampled_at)["status"] == "growing_backlog"


def test_release_change_restarts_acceptance_without_resetting_work() -> None:
    first = AcceptanceSample(NOW, healthy=True, eligible=0, terminal_replays=0, release_sha="old")
    next_sample = replace(first, sampled_at=NOW + timedelta(minutes=1), release_sha="new")
    assert assess_acceptance([first, next_sample], next_sample.sampled_at)["seconds"] == 0
