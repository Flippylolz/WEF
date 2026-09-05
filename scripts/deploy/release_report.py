"""Build a truthful release outcome from allowlisted Actions and host observations."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.deploy.release_observation import clean_observation

DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
CONCLUSIONS = {
    "success",
    "failure",
    "cancelled",
    "skipped",
    "timed_out",
    "action_required",
}


def timestamp(value: object) -> str | None:
    """Normalize a timezone-aware timestamp; preserve unknown data as null."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed.astimezone(UTC).isoformat() if parsed.tzinfo else None


def duration(start: object, end: object) -> dict[str, Any]:
    """Return explicit missing/reversed timestamp evidence instead of fabricated latency."""
    first, last = timestamp(start), timestamp(end)
    if first is None or last is None:
        return {"seconds": None, "unavailable_reason": "missing_timestamp"}
    seconds = (datetime.fromisoformat(last) - datetime.fromisoformat(first)).total_seconds()
    if seconds < 0:
        return {"seconds": None, "unavailable_reason": "reversed_timestamps"}
    return {"seconds": seconds, "unavailable_reason": None}


def stage(raw: dict[str, Any]) -> dict[str, Any]:
    """Project public job/step timing fields only, without logs or environment values."""
    return {
        "name": str(raw.get("name", "unknown"))[:160].replace("\n", " "),
        "conclusion": raw.get("conclusion") if raw.get("conclusion") in CONCLUSIONS else None,
        "started_at": timestamp(raw.get("started_at")),
        "completed_at": timestamp(raw.get("completed_at")),
        "duration": duration(raw.get("started_at"), raw.get("completed_at")),
    }


def interval_gap(start: object, end: object, children: list[dict[str, Any]]) -> dict[str, Any]:
    """Measure uncovered wall time using interval union, including overlapping stages once."""
    span = duration(start, end)
    if span["seconds"] is None:
        return span
    first, last = timestamp(start), timestamp(end)
    if first is None or last is None:
        return span
    intervals: list[tuple[str, str]] = []
    for child in children:
        if child.get("conclusion") == "skipped":
            continue
        a, b = timestamp(child.get("started_at")), timestamp(child.get("completed_at"))
        if a is None or b is None or a > b or a < first or b > last:
            return {"seconds": None, "unavailable_reason": "incomplete_child_intervals"}
        intervals.append((a, b))
    covered = 0.0
    cursor = first
    for a, b in sorted(intervals):
        if b > cursor:
            covered += (
                datetime.fromisoformat(b) - datetime.fromisoformat(max(cursor, a))
            ).total_seconds()
            cursor = b
    return {"seconds": max(0.0, span["seconds"] - covered), "unavailable_reason": None}


def deployment_result(  # noqa: PLR0911 - explicit terminal outcomes are intentionally separate
    *,
    verified: bool,
    eligible: bool,
    deploy: str,
    observed: dict[str, Any],
) -> str:
    """Separate actual activation from job completion and repeated same-SHA work."""
    if not verified:
        return "verification_failed"
    if not eligible:
        return "verified_only"
    if observed.get("restored_at") and observed.get("restored_sha"):
        return "failed_restored"
    if observed.get("superseded_at"):
        return "superseded"
    if observed.get("activated_at") and observed.get("healthy_at"):
        return (
            "already_current"
            if observed.get("previous_sha") == observed["release_sha"]
            else "deployed"
        )
    if observed.get("already_current_at") and observed.get("healthy_at"):
        return "already_current"
    if deploy in {"failure", "cancelled", "timed_out"}:
        return "failed"
    if deploy in {"", "queued", "in_progress"}:
        return "queued"
    return "deployment_unconfirmed"


def build_report(
    needs: dict[str, Any],
    run: dict[str, Any],
    jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the v1 outcome; callers cannot infer health from workflow success."""
    resolve = needs.get("resolve", {}).get("outputs", {})
    sha = resolve.get("release_sha", "")
    try:
        raw = json.loads(needs.get("deploy", {}).get("outputs", {}).get("observation") or "{}")
    except (ValueError, TypeError):
        raw = {}
    observation = clean_observation(raw if isinstance(raw, dict) else {}, sha)
    verified = needs.get("verify", {}).get("result") == "success" or (
        needs.get("publish", {}).get("result") == "success"
        and needs.get("publish", {}).get("outputs", {}).get("reused_verified") == "true"
    )
    eligible = resolve.get("should_deploy") == "true"
    deploy = needs.get("deploy", {}).get("result", "")
    result = deployment_result(
        verified=verified, eligible=eligible, deploy=deploy, observed=observation
    )
    stages = [
        {
            **stage(job),
            "steps": [stage(step) for step in job.get("steps", [])],
            "unattributed_job_time": interval_gap(
                job.get("started_at"), job.get("completed_at"), job.get("steps", [])
            ),
        }
        for job in jobs
        if job.get("name") != "Release outcome"
    ]
    started = [s["started_at"] for s in stages if s["started_at"]]
    completed = [s["completed_at"] for s in stages if s["completed_at"]]
    published = needs.get("publish", {}).get("outputs", {})
    return {
        "schema": "wef-release-outcome/v1",
        "release_sha": sha if re.fullmatch(r"[0-9a-f]{40}", sha) else None,
        "run_id": run.get("id"),
        "run_attempt": run.get("run_attempt"),
        "event": run.get("event") if run.get("event") in {"push", "workflow_dispatch"} else None,
        "gate_reason": resolve.get("gate_reason", "resolution_unavailable"),
        "eligible": eligible,
        "verified": verified,
        "outcome": result,
        "deployment_job_result": deploy if deploy in CONCLUSIONS else None,
        "merged_at": timestamp(resolve.get("merged_at")),
        "created_at": timestamp(run.get("created_at")),
        "healthy_sha": (
            observation.get("restored_sha")
            if result == "failed_restored"
            else sha
            if result in {"deployed", "already_current"}
            else None
        ),
        "observation": observation,
        "merge_to_healthy": duration(
            resolve.get("merged_at"),
            observation.get("healthy_at") if result == "deployed" else None,
        ),
        "event_to_first_job": duration(run.get("created_at"), min(started) if started else None),
        "between_job_gaps": interval_gap(
            min(started) if started else None,
            max(completed) if completed else None,
            stages,
        ),
        "activation": duration(observation.get("started_at"), observation.get("activated_at")),
        "rollback": duration(
            observation.get("rollback_started_at"), observation.get("restored_at")
        ),
        "images": {
            name: value if isinstance(value, str) and DIGEST.fullmatch(value) else None
            for name, value in (
                ("backend", published.get("backend_digest")),
                ("web", published.get("web_digest")),
            )
        },
        "cache_state": "unknown",
        "cache_unavailable_reason": "cache_hit_not_instrumented",
        "stages": stages,
        "timing_definition": (
            "UTC observed health is an upper bound; job gaps include dependencies and runner waits"
        ),
        "reporting_errors": [] if run and jobs else ["actions_metadata_unavailable"],
    }


def render_summary(report: dict[str, Any]) -> str:
    """Render the same sanitized outcome as a human-readable Actions summary."""
    lines = [
        "## Release outcome",
        "",
        f"**{report['outcome']}** — `{report['release_sha']}`",
        "",
        f"Gate: `{report['gate_reason']}`. Healthy SHA: `{report['healthy_sha']}`.",
        "",
    ]
    for name in ("merge_to_healthy", "event_to_first_job", "activation", "rollback"):
        metric = report[name]
        value = (
            f"{metric['seconds']} s"
            if metric["seconds"] is not None
            else f"unavailable ({metric['unavailable_reason']})"
        )
        lines.append(f"- {name}: {value}")
    lines += ["", "| Stage | Result | Seconds |", "| --- | --- | --- |"]
    for item in report["stages"]:
        name = item["name"].replace("|", "\\|").replace("<", "&lt;")
        seconds = item["duration"]["seconds"]
        value = seconds if seconds is not None else "unavailable"
        lines.append(f"| {name} | {item['conclusion']} | {value} |")
    lines += [
        "",
        report["timing_definition"],
        "Cache state: unknown; no cache evidence is inferred.",
        "",
    ]
    return "\n".join(lines)


def read_api(endpoint: str) -> dict[str, Any]:
    """Retry bounded read-only metadata requests without printing response bodies."""
    executable = shutil.which("gh")
    if executable is None:
        return {}
    for delay in (0, 5, 15):
        if delay:
            time.sleep(delay)
        try:
            result = subprocess.run(  # noqa: S603 - fixed gh API command, no shell
                [executable, "api", endpoint],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            continue
        if result.returncode == 0:
            raw = json.loads(result.stdout)
            if isinstance(raw, dict):
                return raw
    return {}


def main() -> int:
    """Collect this attempt's metadata and publish only the bounded outcome projection."""
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    repo, run_id, attempt = (
        os.environ[key] for key in ("GITHUB_REPOSITORY", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")
    )
    run = read_api(f"repos/{repo}/actions/runs/{run_id}/attempts/{attempt}")
    jobs = read_api(f"repos/{repo}/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100")
    report = build_report(json.loads(os.environ["RELEASE_NEEDS"]), run, jobs.get("jobs", []))
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as stream:
        stream.write(render_summary(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
