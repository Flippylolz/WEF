"""Deadline-aware progress health independent of transport and process liveness."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

MIN_STAGNANT_SAMPLES = 3
SAMPLE_SECONDS = 60
STALL_SECONDS = 300
MAX_SAMPLE_GAP = 120
HEALTHY_STATES = frozenset({"idle", "progressing", "waiting", "in_flight"})


@dataclass(frozen=True, slots=True)
class ProgressSnapshot:
    """Disjoint work populations plus separately named cumulative observations."""

    stage: str
    token: str
    eligible: int = 0
    delayed: int = 0
    leased: int = 0
    terminal: int = 0
    quarantined: int = 0
    completed: int = 0
    attempted: int | None = None
    deferred: int | None = None
    oldest_due: datetime | None = None
    wait_until: datetime | None = None
    paused: bool = False
    actionable_pause: bool = False
    terminal_replays: int = 0

    @property
    def total(self) -> int:
        """Each queued identity belongs to exactly one population."""
        return self.eligible + self.delayed + self.leased + self.terminal + self.quarantined


@dataclass(frozen=True, slots=True)
class ProgressCheckpoint:
    """Persist comparison and incident recovery state across process lifetimes."""

    token: str
    sampled_at: datetime
    progressed_at: datetime
    stagnant_samples: int = 0
    healthy_samples: int = 0
    status: str = "observing"
    reason: str | None = None
    terminal_replays: int = 0
    replay_samples: int = 0


def classify_progress(
    snapshot: ProgressSnapshot, previous: ProgressCheckpoint | None, now: datetime
) -> ProgressCheckpoint:
    """Count unique transitions; attempts and quarantine never masquerade as success."""
    discontinuous = (
        previous is None or not 0 < (now - previous.sampled_at).total_seconds() <= MAX_SAMPLE_GAP
    )
    changed = previous is None or snapshot.token != previous.token
    progressed = now if previous is None or changed or discontinuous else previous.progressed_at
    stagnant = 0 if previous is None or changed or discontinuous else previous.stagnant_samples + 1
    replay_samples = (
        previous.replay_samples + 1
        if previous is not None
        and not discontinuous
        and snapshot.terminal_replays > previous.terminal_replays
        else 0
    )
    reason = None
    if discontinuous:
        status = "observing"
    elif replay_samples >= MIN_STAGNANT_SAMPLES:
        status = "stalled"
        reason = "repeated_terminal_work"
    elif snapshot.paused:
        status = "paused"
        reason = "systemic_pause" if snapshot.actionable_pause else None
    elif snapshot.wait_until is not None and now <= snapshot.wait_until + timedelta(seconds=120):
        status = "waiting"
    elif snapshot.leased:
        status = "in_flight"
    elif (
        snapshot.stage == "offer_delivery"
        and snapshot.eligible
        and snapshot.oldest_due
        and (now - snapshot.oldest_due).total_seconds() >= STALL_SECONDS
    ):
        status = "stalled"
        reason = "offer_delivery_deadline"
    elif snapshot.eligible:
        since = max(progressed, snapshot.oldest_due or progressed)
        if stagnant >= MIN_STAGNANT_SAMPLES and (now - since).total_seconds() >= STALL_SECONDS:
            status = "stalled"
            reason = "eligible_without_unique_progress"
        else:
            status = "progressing"
    elif snapshot.delayed:
        status = "waiting"
    else:
        status = "idle"
    healthy = (
        (previous.healthy_samples if previous and not discontinuous else 0) + 1
        if status in HEALTHY_STATES
        else 0
    )
    return ProgressCheckpoint(
        snapshot.token,
        now,
        progressed,
        stagnant,
        healthy,
        status,
        reason,
        snapshot.terminal_replays,
        replay_samples,
    )


@dataclass(frozen=True, slots=True)
class AcceptanceSample:
    """Minimal safe evidence needed for a continuous reliability window."""

    sampled_at: datetime
    healthy: bool
    eligible: int
    terminal_replays: int
    release_sha: str | None = None


def assess_acceptance(samples: list[AcceptanceSample], now: datetime) -> dict[str, object]:
    """Restart the window after invalid evidence; never manufacture missing time."""
    if not samples:
        return {"status": "collecting", "seconds": 0}
    start = 0
    for index, sample in enumerate(samples):
        if not sample.healthy:
            start = index + 1
        elif index:
            previous = samples[index - 1]
            delta = (sample.sampled_at - previous.sampled_at).total_seconds()
            if (
                not 0 < delta <= MAX_SAMPLE_GAP
                or sample.terminal_replays != previous.terminal_replays
                or sample.release_sha != previous.release_sha
            ):
                start = index
    if start == len(samples):
        return {"status": "unhealthy", "seconds": 0}
    first, last = samples[start], samples[-1]
    seconds = max(0, int((last.sampled_at - first.sampled_at).total_seconds()))
    fresh = 0 <= (now - last.sampled_at).total_seconds() <= MAX_SAMPLE_GAP
    status = "collecting"
    if not fresh:
        status = "sampling_gap"
    elif last.eligible > first.eligible:
        status = "growing_backlog"
    elif seconds >= 24 * 60 * 60:
        status = "passed"
    return {"status": status, "seconds": seconds, "started_at": first.sampled_at.isoformat()}
