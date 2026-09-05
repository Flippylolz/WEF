"""Collect bounded release evidence and assess latency without inventing successful deployments."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, TypeGuard

from scripts.deploy.release_report import duration, read_api, timestamp

SHA = re.compile(r"^[0-9a-f]{40}$")
MAX_REPORT_BYTES = 1_000_000
MAX_RUNS = 100
MINIMUM_SAMPLES = 20
P50_BUDGET = 300
P95_BUDGET = 420
CACHE_STATES = {"warm", "cold", "mixed", "unknown"}
OUTCOMES = {
    "deployed",
    "already_current",
    "superseded",
    "verified_only",
    "verification_failed",
    "failed",
    "failed_restored",
    "preparation_failed",
    "queued",
    "deployment_unconfirmed",
}


def percentile(values: list[float], fraction: float) -> float | None:
    """Use nearest rank; empty samples have no estimated percentile."""
    return sorted(values)[math.ceil(len(values) * fraction) - 1] if values else None


def stats(values: list[float]) -> dict[str, Any]:
    """Report sample count alongside each percentile."""
    return {
        "samples": len(values),
        "p50_seconds": percentile(values, 0.5),
        "p95_seconds": percentile(values, 0.95),
    }


def valid_seconds(value: object) -> TypeGuard[int | float]:
    """Reject booleans, negative, non-finite and untyped durations."""
    return (
        isinstance(value, (float, int))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def summarize(records: list[dict[str, Any]], optimized_from: str | None) -> dict[str, Any]:
    """Keep failures in counts; deduplicate successful observations by source SHA for budgets."""
    unique = {(r["run_id"], r["run_attempt"]): r for r in records}
    rows = list(unique.values())
    ordinary = [r for r in rows if r.get("event") == "push" and r.get("merged_at")]
    cohorts: dict[str, Any] = {}
    for phase in ("baseline", "optimized", "unclassified"):
        selected = [r for r in ordinary if r.get("phase") == phase]
        healthy: dict[str, float] = {}
        job_end: dict[str, float] = {}
        for r in selected:
            sha = r["release_sha"]
            seconds = r.get("merge_to_healthy_seconds")
            if r.get("outcome") == "deployed" and valid_seconds(seconds):
                healthy[sha] = min(healthy.get(sha, float("inf")), float(seconds))
            value = r.get("merge_to_deploy_job_end_seconds")
            if r.get("deploy_job_result") == "success" and valid_seconds(value):
                job_end[sha] = min(job_end.get(sha, float("inf")), float(value))
        cohorts[phase] = {
            "ordinary_runs": len(selected),
            "unique_sources": len({r["release_sha"] for r in selected}),
            "outcomes": dict(Counter(r["outcome"] for r in selected)),
            "run_conclusions": dict(Counter(r["run_conclusion"] for r in selected)),
            "merge_to_healthy": stats(list(healthy.values())),
            "merge_to_deploy_job_end": stats(list(job_end.values())),
            "initial_queue": stats(
                [
                    float(r["initial_queue_seconds"])
                    for r in selected
                    if valid_seconds(r.get("initial_queue_seconds"))
                ]
            ),
            "cache_states": dict(Counter(r["cache_state"] for r in selected)),
            "missing_health_runs": sum(r.get("merge_to_healthy_seconds") is None for r in selected),
            "human_interventions": None,
            "intervention_unavailable_reason": (
                "SSH and operator actions cannot be inferred from workflow events"
            ),
            "provider_runner_incidents": "unattributed; all runs remain included",
        }
    metrics = cohorts["optimized"]["merge_to_healthy"]
    status = "awaiting_cutoff" if optimized_from is None else "insufficient_observations"
    if optimized_from is not None and metrics["samples"] >= MINIMUM_SAMPLES:
        status = (
            "met"
            if metrics["p50_seconds"] <= P50_BUDGET and metrics["p95_seconds"] <= P95_BUDGET
            else "missed"
        )
    return {
        "schema": "wef-release-cohort/v1",
        "optimized_from": optimized_from,
        "run_attempts": len(rows),
        "duplicate_records_ignored": len(records) - len(rows),
        "manual_dispatches": sum(r.get("event") == "workflow_dispatch" for r in rows),
        "unmatched_pushes": sum(r.get("event") == "push" and not r.get("merged_at") for r in rows),
        "cohorts": cohorts,
        "latency_budget": {
            "status": status,
            "minimum_unique_healthy_sources": MINIMUM_SAMPLES,
            "p50_seconds": P50_BUDGET,
            "p95_seconds": P95_BUDGET,
        },
        "operational_acceptance": (
            "pending separate cache, consecutive-merge, rollback and operator evidence"
        ),
        "measurement": (
            "nearest-rank; merge-to-observed-health includes queue time; "
            "job end is a separate metric"
        ),
    }


def trusted_observation(report: dict[str, Any], run: dict[str, Any]) -> bool:
    """Require same-run, same-attempt, exact-SHA evidence before accepting first-health timing."""
    return (
        report.get("schema") == "wef-release-outcome/v1"
        and report.get("release_sha") == run.get("head_sha")
        and report.get("run_id") == run.get("id")
        and report.get("run_attempt") == run.get("run_attempt")
        and report.get("event") == run.get("event")
    )


def observation(repo: str, run: dict[str, Any]) -> dict[str, Any]:
    """Download one named outcome into temporary storage; missing artifacts stay unavailable."""
    gh = shutil.which("gh")
    if gh is None:
        return {}
    name = f"release-outcome-{run['id']}-{run['run_attempt']}"
    artifacts = read_api(f"repos/{repo}/actions/runs/{run['id']}/artifacts?per_page=100")
    if not any(
        a.get("name") == name and a.get("expired") is False for a in artifacts.get("artifacts", [])
    ):
        return {}
    with tempfile.TemporaryDirectory() as directory:
        try:
            result = subprocess.run(  # noqa: S603 - fixed gh command with API run identity
                [
                    gh,
                    "run",
                    "download",
                    str(run["id"]),
                    "--repo",
                    repo,
                    "--name",
                    name,
                    "--dir",
                    directory,
                ],
                capture_output=True,
                check=False,
                timeout=60,
            )
            path = Path(directory) / "release-outcome.json"
            if result.returncode or path.is_symlink() or path.stat().st_size > MAX_REPORT_BYTES:
                return {}
            report = json.loads(path.read_text())
            return report if isinstance(report, dict) and trusted_observation(report, run) else {}
        except (ValueError, OSError, subprocess.TimeoutExpired):
            return {}


def collect_record(repo: str, run: dict[str, Any], optimized_from: str | None) -> dict[str, Any]:
    """Project only SHA, outcomes and timings without source content, logs or configuration."""
    sha, run_id, attempt = run["head_sha"], run["id"], run["run_attempt"]
    prs = read_api(f"repos/{repo}/commits/{sha}/pulls", wrap_list=True).get("items", [])
    merged = next(
        (
            p.get("merged_at")
            for p in prs
            if p.get("state") == "closed"
            and p.get("merge_commit_sha") == sha
            and p.get("base", {}).get("ref") == "main"
            and p.get("merged_at")
        ),
        None,
    )
    jobs = read_api(f"repos/{repo}/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100").get(
        "jobs", []
    )
    deploy: dict[str, Any] = next(
        (j for j in jobs if j.get("name") == "Deploy verified release"), {}
    )
    started = [value for j in jobs if (value := timestamp(j.get("started_at"))) is not None]
    report = observation(repo, run)
    healthy = None
    if (
        report.get("outcome") == "deployed"
        and report.get("verified") is True
        and report.get("eligible") is True
        and report.get("healthy_sha") == sha
    ):
        observed = report.get("observation", {})
        if (
            observed.get("release_sha") == sha
            and duration(observed.get("healthy_at"), observed.get("activated_at"))["seconds"]
            is not None
        ):
            healthy = observed.get("healthy_at")
    phase = "unclassified"
    if optimized_from is not None:
        comparison = read_api(f"repos/{repo}/compare/{optimized_from}...{sha}").get("status")
        if comparison in {"ahead", "identical"}:
            phase = "optimized"
        elif comparison == "behind":
            phase = "baseline"
    return {
        "run_id": run_id,
        "run_attempt": attempt,
        "release_sha": sha,
        "event": run.get("event"),
        "run_conclusion": run.get("conclusion") or "pending",
        "phase": phase,
        "merged_at": timestamp(merged),
        "deploy_job_result": deploy.get("conclusion"),
        "outcome": report.get("outcome")
        if report.get("outcome") in OUTCOMES
        else "deployment_unconfirmed",
        "merge_to_healthy_seconds": duration(merged, healthy)["seconds"],
        "merge_to_deploy_job_end_seconds": duration(
            merged, deploy.get("completed_at") if deploy.get("conclusion") == "success" else None
        )["seconds"],
        "initial_queue_seconds": duration(run.get("created_at"), min(started) if started else None)[
            "seconds"
        ],
        "cache_state": report.get("cache_state")
        if report.get("cache_state") in CACHE_STATES
        else "unknown",
        "artifact_available": bool(report),
    }


def clean_records(raw: object) -> list[dict[str, Any]]:
    """Validate saved evidence identities and discard unrecognized input fields."""
    if not isinstance(raw, list):
        msg = "saved evidence must contain a records array"
        raise TypeError(msg)
    clean = []
    for record in raw:
        if (
            not isinstance(record, dict)
            or type(record.get("run_id")) is not int
            or type(record.get("run_attempt")) is not int
            or record["run_id"] < 1
            or record["run_attempt"] < 1
            or not isinstance(record.get("release_sha"), str)
            or not SHA.fullmatch(record["release_sha"])
        ):
            msg = "saved evidence has invalid run or source identity"
            raise ValueError(msg)
        item = {key: record[key] for key in ("run_id", "run_attempt", "release_sha")}
        for key, allowed, default in (
            ("phase", {"baseline", "optimized", "unclassified"}, "unclassified"),
            ("event", {"push", "workflow_dispatch"}, None),
            ("outcome", OUTCOMES, "deployment_unconfirmed"),
            ("cache_state", CACHE_STATES, "unknown"),
            ("run_conclusion", {"success", "failure", "cancelled", "pending"}, "pending"),
            ("deploy_job_result", {"success", "failure", "cancelled", "skipped"}, None),
        ):
            value = record.get(key)
            item[key] = value if isinstance(value, str) and value in allowed else default
        item["merged_at"] = timestamp(record.get("merged_at"))
        item["artifact_available"] = record.get("artifact_available") is True
        for key in (
            "merge_to_healthy_seconds",
            "merge_to_deploy_job_end_seconds",
            "initial_queue_seconds",
        ):
            value = record.get(key)
            item[key] = value if valid_seconds(value) else None
        clean.append(item)
    return clean


def render(result: dict[str, Any]) -> str:
    """Render a compact comparison that distinguishes measurement gaps from target failures."""
    lines = [
        "# Release performance evidence",
        "",
        f"Latency target: **{result['latency_budget']['status']}**.",
        "",
        result["measurement"],
        "",
        "| Cohort | Runs | Healthy samples | p50 health (s) | p95 health (s) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, cohort in result["cohorts"].items():
        metric = cohort["merge_to_healthy"]
        lines.append(
            f"| {name} | {cohort['ordinary_runs']} | {metric['samples']} | "
            f"{metric['p50_seconds']} | {metric['p95_seconds']} |"
        )
    lines += [
        "",
        (
            f"Manual dispatches: {result['manual_dispatches']}. "
            f"Unmatched pushes: {result['unmatched_pushes']}."
        ),
        "",
        (
            "Human interventions and provider/runner incidents require separate evidence; "
            "they are not assumed to be zero."
        ),
        result["operational_acceptance"],
        "",
    ]
    return "\n".join(lines)


def load_saved(path: Path, cutoff: str | None) -> tuple[list[dict[str, Any]], str | None]:
    """Load sanitized evidence without relabeling a previously collected source cohort."""
    saved = json.loads(path.read_text())
    if (
        not isinstance(saved, dict)
        or saved.get("summary", {}).get("schema") != "wef-release-cohort/v1"
    ):
        msg = "saved evidence has an unsupported schema"
        raise ValueError(msg)
    previous_cutoff = saved["summary"].get("optimized_from")
    if previous_cutoff is not None and (
        not isinstance(previous_cutoff, str) or not SHA.fullmatch(previous_cutoff)
    ):
        msg = "saved evidence has an invalid optimization cutoff"
        raise ValueError(msg)
    if cutoff is not None and previous_cutoff != cutoff:
        msg = "recollect source ancestry when changing the optimization cutoff"
        raise ValueError(msg)
    return clean_records(saved.get("records")), previous_cutoff


def main() -> int:
    """Collect up to 100 recent runs or summarize an existing sanitized evidence file."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Flippylolz/WEF")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--optimized-from")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-budget", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.limit <= MAX_RUNS or not re.fullmatch(
        r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo
    ):
        parser.error("require a valid repository and a limit between 1 and 100")
    if args.optimized_from is not None and not SHA.fullmatch(args.optimized_from):
        parser.error("optimized-from must be the full merged optimization SHA")
    records: list[dict[str, Any]] = []
    if args.input:
        records, args.optimized_from = load_saved(args.input, args.optimized_from)
    if args.input is None:
        runs = read_api(
            f"repos/{args.repo}/actions/workflows/deploy-production.yml/runs?branch=main&per_page={args.limit}"
        )
        if "workflow_runs" not in runs:
            parser.error("release run metadata is unavailable; no evidence was written")
        for run in runs["workflow_runs"]:
            if (
                run.get("head_repository", {}).get("full_name") == args.repo
                and SHA.fullmatch(run.get("head_sha", ""))
                and run.get("head_branch") == "main"
            ):
                records.append(collect_record(args.repo, run, args.optimized_from))
    result = summarize(records, args.optimized_from)
    args.output.write_text(json.dumps({"summary": result, "records": records}, indent=2) + "\n")
    args.output.with_suffix(".md").write_text(render(result))
    return int(args.require_budget and result["latency_budget"]["status"] != "met")


if __name__ == "__main__":
    raise SystemExit(main())
