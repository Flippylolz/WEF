"""Scheduled Dependabot merge controller (default-branch only; no PR checkout)."""

from __future__ import annotations

# ruff: noqa: C901, D101, D103, PLR0911, PLR0912, T201, TRY004
import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKS_PATH = REPOSITORY_ROOT / ".github" / "dependabot-required-checks.json"
AUTOMERGE_LABEL = "automerge"
DEPENDABOT_LOGIN = "dependabot[bot]"
# gh GraphQL `author.login` is `app/dependabot`; REST commit authors use `dependabot[bot]`.
DEPENDABOT_AUTHOR_LOGINS = frozenset({DEPENDABOT_LOGIN, "app/dependabot"})
ALLOWED_COMMITTERS = frozenset({*DEPENDABOT_AUTHOR_LOGINS, "web-flow"})
DEFAULT_OWNER_ALLOWLIST = frozenset({"Flippylolz"})
ALLOWED_UPDATE_TYPES = frozenset(
    {
        "version-update:semver-patch",
        "version-update:semver-minor",
    }
)
FROM_TO_RE = re.compile(
    r"from\s+v?(?P<old>\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.]+)?)\s+to\s+v?(?P<new>\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.]+)?)",
    re.IGNORECASE,
)
BAD_CHECK_STATES = frozenset(
    {
        "PENDING",
        "QUEUED",
        "IN_PROGRESS",
        "WAITING",
        "REQUESTED",
        "EXPECTED",
        "FAILURE",
        "ERROR",
        "CANCELLED",
        "TIMED_OUT",
        "STALE",
        "ACTION_REQUIRED",
        "STARTUP_FAILURE",
    }
)
SUCCESS_CHECK_STATES = frozenset({"SUCCESS", "SKIPPED", "NEUTRAL"})

CommandRunner = Callable[[Sequence[str]], str]
DecisionAction = Literal["merge", "defer", "reject"]


@dataclass(frozen=True, slots=True)
class Decision:
    action: DecisionAction
    reason: str


@dataclass(frozen=True, slots=True)
class PullRequestSnapshot:
    number: int
    title: str
    state: str
    is_draft: bool
    base_ref: str
    head_ref: str
    head_oid: str
    author_login: str
    labels: frozenset[str]
    mergeable: str | None
    body: str
    commits: tuple[dict[str, object], ...]
    checks: tuple[dict[str, object], ...]
    label_events: tuple[dict[str, object], ...]
    behind_by: int
    update_types: frozenset[str]
    dependency_types: frozenset[str]


def load_required_checks(path: Path) -> tuple[str, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"expected object in {path}"
        raise ValueError(msg)
    names = payload.get("required_check_names")
    if not isinstance(names, list) or not names or not all(isinstance(n, str) and n for n in names):
        msg = f"required_check_names must be a non-empty string list in {path}"
        raise ValueError(msg)
    return tuple(names)


def _run_gh(args: Sequence[str], *, runner: CommandRunner | None = None) -> str:
    command = ["gh", *args]
    if runner is not None:
        return runner(command)
    completed = subprocess.run(command, check=False, capture_output=True, text=True)  # noqa: S603
    if completed.returncode != 0:
        detail = (
            completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}"
        )
        msg = f"gh command failed: {' '.join(command)} ({detail})"
        raise RuntimeError(msg)
    return completed.stdout


def _parse_semver(value: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:[-+].*)?", value)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def classify_semver_update(old: str, new: str) -> str | None:
    left = _parse_semver(old)
    right = _parse_semver(new)
    if left is None or right is None:
        return None
    if right[0] != left[0]:
        return "version-update:semver-major"
    if right[1] != left[1]:
        return "version-update:semver-minor"
    if right[2] != left[2]:
        return "version-update:semver-patch"
    return None


def infer_update_metadata(
    title: str, body: str, head_ref: str
) -> tuple[frozenset[str], frozenset[str]]:
    """Infer Dependabot update/dependency types without PR checkout."""
    update_types: set[str] = set()
    dependency_types: set[str] = {"direct"}
    text = f"{title}\n{body}"
    for match in FROM_TO_RE.finditer(text):
        classified = classify_semver_update(match.group("old"), match.group("new"))
        if classified is not None:
            update_types.add(classified)
    if "patch-minor" in head_ref and not update_types:
        update_types.add("version-update:semver-patch")
    if re.search(r"\bmajor\b", head_ref, re.IGNORECASE):
        update_types.add("version-update:semver-major")
    if re.search(r"(?i)\bindirect\b", text):
        dependency_types.add("indirect")
        dependency_types.discard("direct")
    return frozenset(update_types), frozenset(dependency_types)


def evaluate_candidate(
    pr: PullRequestSnapshot,
    *,
    required_checks: Sequence[str],
    owner_allowlist: frozenset[str],
    repository: str,
) -> Decision:
    if pr.state != "OPEN":
        return Decision("reject", "pull request is not open")
    if pr.is_draft:
        return Decision("reject", "pull request is draft")
    if pr.base_ref != "main":
        return Decision("reject", "base branch is not main")
    if pr.author_login not in DEPENDABOT_AUTHOR_LOGINS:
        return Decision("reject", "author is not dependabot[bot]")
    if not pr.head_ref.startswith("dependabot/"):
        return Decision("reject", "head branch does not start with dependabot/")
    if AUTOMERGE_LABEL not in pr.labels:
        return Decision("defer", "missing automerge label")

    label_actor = _latest_automerge_label_actor(pr.label_events)
    if label_actor is None:
        return Decision("reject", "automerge label actor could not be verified")
    if label_actor not in owner_allowlist:
        return Decision("reject", f"automerge label actor {label_actor!r} is not allowlisted")

    if not pr.update_types:
        return Decision("reject", "could not classify Dependabot update type as patch/minor")
    if any(item not in ALLOWED_UPDATE_TYPES for item in pr.update_types):
        return Decision(
            "reject", f"update types not limited to patch/minor: {sorted(pr.update_types)}"
        )
    if "indirect" in pr.dependency_types or "direct" not in pr.dependency_types:
        return Decision("reject", "update is not a direct dependency update")

    for commit in pr.commits:
        author = str(commit.get("author_login") or "")
        committer = str(commit.get("committer_login") or "")
        if author not in DEPENDABOT_AUTHOR_LOGINS:
            return Decision("reject", f"commit author {author!r} is not dependabot[bot]")
        if committer not in ALLOWED_COMMITTERS:
            return Decision("reject", f"commit committer {committer!r} is not an allowed bot")

    if pr.behind_by > 0:
        return Decision(
            "defer", "head does not include current main; waiting for Dependabot rebase"
        )

    check_by_name = {str(check.get("name")): check for check in pr.checks if check.get("name")}
    for required in required_checks:
        check = check_by_name.get(required)
        if check is None:
            return Decision("defer", f"required check {required!r} is missing on head")
        state = str(check.get("state") or "").upper()
        if state not in SUCCESS_CHECK_STATES:
            return Decision("defer", f"required check {required!r} is {state or 'unknown'}")

    for check in pr.checks:
        name = str(check.get("name") or "unknown")
        state = str(check.get("state") or "").upper()
        if state in BAD_CHECK_STATES:
            return Decision("defer", f"check {name!r} is {state}")
        if state and state not in SUCCESS_CHECK_STATES:
            return Decision("defer", f"check {name!r} has unexpected state {state}")

    mergeable = (pr.mergeable or "").upper()
    if mergeable in {"CONFLICTING", "FALSE"}:
        return Decision("defer", "pull request has merge conflicts")
    if mergeable in {"UNKNOWN", ""}:
        return Decision("defer", "mergeability is not yet known")
    if mergeable not in {"MERGEABLE", "TRUE"}:
        return Decision("defer", f"mergeability is {mergeable}")

    return Decision("merge", f"eligible to squash-merge into {repository}@main")


def _latest_automerge_label_actor(events: Sequence[Mapping[str, object]]) -> str | None:
    actor: str | None = None
    for event in events:
        if str(event.get("event") or "") != "labeled":
            continue
        label = event.get("label")
        label_name = ""
        if isinstance(label, Mapping):
            label_name = str(label.get("name") or "")
        elif isinstance(label, str):
            label_name = label
        if label_name != AUTOMERGE_LABEL:
            continue
        actor = str(event.get("actor_login") or "") or None
    return actor


def _status_state(check: Mapping[str, object]) -> str:
    conclusion = str(check.get("conclusion") or "").upper()
    status = str(check.get("status") or "").upper()
    state = str(check.get("state") or "").upper()
    if conclusion:
        return conclusion
    if state:
        return state
    if status == "COMPLETED":
        return "SUCCESS"
    return status or "PENDING"


def _as_mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    return {}


def fetch_pull_request(
    number: int,
    *,
    repository: str,
    runner: CommandRunner | None = None,
) -> PullRequestSnapshot:
    owner, _, repo = repository.partition("/")
    view_raw = _run_gh(
        [
            "pr",
            "view",
            str(number),
            "--repo",
            repository,
            "--json",
            "number,title,state,isDraft,baseRefName,headRefName,headRefOid,author,labels,mergeable,body,commits,statusCheckRollup",
        ],
        runner=runner,
    )
    view = json.loads(view_raw)
    commits_raw = _run_gh(
        ["api", f"repos/{owner}/{repo}/pulls/{number}/commits", "--paginate"],
        runner=runner,
    )
    commits_payload = json.loads(commits_raw)
    events_raw = _run_gh(
        ["api", f"repos/{owner}/{repo}/issues/{number}/events", "--paginate"],
        runner=runner,
    )
    events_payload = json.loads(events_raw)
    head_oid = str(view.get("headRefOid") or "")
    compare_raw = _run_gh(
        ["api", f"repos/{owner}/{repo}/compare/main...{head_oid}"],
        runner=runner,
    )
    compare = json.loads(compare_raw)

    author = _as_mapping(view.get("author"))
    labels = frozenset(
        str(item.get("name"))
        for item in (view.get("labels") or [])
        if isinstance(item, dict) and item.get("name")
    )
    commits: list[dict[str, object]] = []
    for item in commits_payload if isinstance(commits_payload, list) else []:
        if not isinstance(item, dict):
            continue
        author_obj = _as_mapping(item.get("author"))
        committer_obj = _as_mapping(item.get("committer"))
        commit_obj = _as_mapping(item.get("commit"))
        commit_author = _as_mapping(commit_obj.get("author"))
        commit_committer = _as_mapping(commit_obj.get("committer"))
        author_login = str(author_obj.get("login") or "")
        committer_login = str(committer_obj.get("login") or "")
        if not author_login and str(commit_author.get("name") or "") == "dependabot[bot]":
            author_login = DEPENDABOT_LOGIN
        if not committer_login and str(commit_committer.get("name") or "") in ALLOWED_COMMITTERS:
            committer_login = str(commit_committer.get("name"))
        commits.append(
            {
                "sha": item.get("sha"),
                "author_login": author_login,
                "committer_login": committer_login,
            }
        )

    checks: list[dict[str, object]] = []
    for item in view.get("statusCheckRollup") or []:
        if not isinstance(item, dict):
            continue
        checks.append(
            {
                "name": item.get("name"),
                "state": _status_state(item),
            }
        )

    label_events: list[dict[str, object]] = []
    for item in events_payload if isinstance(events_payload, list) else []:
        if not isinstance(item, dict):
            continue
        actor = _as_mapping(item.get("actor"))
        label = _as_mapping(item.get("label"))
        label_events.append(
            {
                "event": item.get("event"),
                "actor_login": actor.get("login"),
                "label": {"name": label.get("name")},
            }
        )

    title = str(view.get("title") or "")
    body = str(view.get("body") or "")
    head_ref = str(view.get("headRefName") or "")
    update_types, dependency_types = infer_update_metadata(title, body, head_ref)

    return PullRequestSnapshot(
        number=int(view["number"]),
        title=title,
        state=str(view.get("state") or "").upper(),
        is_draft=bool(view.get("isDraft")),
        base_ref=str(view.get("baseRefName") or ""),
        head_ref=head_ref,
        head_oid=head_oid,
        author_login=str(author.get("login") or ""),
        labels=labels,
        mergeable=str(view.get("mergeable") or "") or None,
        body=body,
        commits=tuple(commits),
        checks=tuple(checks),
        label_events=tuple(label_events),
        behind_by=int(compare.get("behind_by") or 0),
        update_types=update_types,
        dependency_types=dependency_types,
    )


def list_automerge_pull_numbers(
    *, repository: str, runner: CommandRunner | None = None
) -> list[int]:
    raw = _run_gh(
        [
            "pr",
            "list",
            "--repo",
            repository,
            "--base",
            "main",
            "--state",
            "open",
            "--label",
            AUTOMERGE_LABEL,
            "--json",
            "number",
        ],
        runner=runner,
    )
    payload = json.loads(raw)
    return [int(item["number"]) for item in payload if isinstance(item, dict) and "number" in item]


def merge_pull_request(
    number: int,
    *,
    head_oid: str,
    repository: str,
    runner: CommandRunner | None = None,
) -> None:
    _run_gh(
        [
            "pr",
            "merge",
            str(number),
            "--repo",
            repository,
            "--squash",
            "--delete-branch",
            "--match-head-commit",
            head_oid,
        ],
        runner=runner,
    )


def process_repository(
    *,
    repository: str,
    required_checks: Sequence[str],
    owner_allowlist: frozenset[str],
    runner: CommandRunner | None = None,
    dry_run: bool = False,
) -> list[tuple[int, Decision]]:
    results: list[tuple[int, Decision]] = []
    for number in list_automerge_pull_numbers(repository=repository, runner=runner):
        first = fetch_pull_request(number, repository=repository, runner=runner)
        decision = evaluate_candidate(
            first,
            required_checks=required_checks,
            owner_allowlist=owner_allowlist,
            repository=repository,
        )
        if decision.action != "merge":
            results.append((number, decision))
            continue

        # Refetch immediately before merge to close label/head/check races.
        second = fetch_pull_request(number, repository=repository, runner=runner)
        if second.head_oid != first.head_oid:
            results.append(
                (number, Decision("reject", "head SHA changed between evaluation and merge"))
            )
            continue
        decision = evaluate_candidate(
            second,
            required_checks=required_checks,
            owner_allowlist=owner_allowlist,
            repository=repository,
        )
        if decision.action != "merge":
            results.append((number, decision))
            continue
        if dry_run:
            results.append(
                (number, Decision("merge", f"dry-run: would merge at {second.head_oid}"))
            )
            continue
        try:
            merge_pull_request(
                number,
                head_oid=second.head_oid,
                repository=repository,
                runner=runner,
            )
        except RuntimeError as exc:
            message = str(exc)
            if "head" in message.lower() and "match" in message.lower():
                results.append((number, Decision("reject", "merge refused: head SHA changed")))
            else:
                results.append((number, Decision("defer", f"merge failed: {message}")))
            continue
        results.append((number, Decision("merge", f"squash-merged at {second.head_oid}")))
    return results


def write_step_summary(results: Sequence[tuple[int, Decision]], path: Path | None) -> None:
    lines = ["## Dependabot merge controller", ""]
    if not results:
        lines.append("No open `automerge`-labeled pull requests.")
    for number, decision in results:
        lines.append(f"- PR #{number}: **{decision.action}** — {decision.reason}")
    text = "\n".join(lines) + "\n"
    print(text)
    if path is not None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(text)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        default="",
        help="owner/name repository (defaults to GITHUB_REPOSITORY)",
    )
    parser.add_argument(
        "--checks-file",
        type=Path,
        default=DEFAULT_CHECKS_PATH,
        help="path to required check-name allowlist JSON",
    )
    parser.add_argument(
        "--owner",
        action="append",
        default=[],
        help="allowlisted automerge label actor (repeatable; default Flippylolz)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    repository = args.repository or os.environ.get("GITHUB_REPOSITORY", "")
    if not repository or "/" not in repository:
        print("repository must be set as owner/name", file=sys.stderr)
        return 2

    owners = frozenset(args.owner) if args.owner else DEFAULT_OWNER_ALLOWLIST
    required = load_required_checks(args.checks_file)
    results = process_repository(
        repository=repository,
        required_checks=required,
        owner_allowlist=owners,
        dry_run=args.dry_run,
    )
    summary = (
        Path(os.environ["GITHUB_STEP_SUMMARY"]) if os.environ.get("GITHUB_STEP_SUMMARY") else None
    )
    write_step_summary(results, summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
