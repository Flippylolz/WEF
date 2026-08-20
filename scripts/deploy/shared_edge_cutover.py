"""Staged shared-edge cutover orchestration with automatic rollback."""

from __future__ import annotations

# ruff: noqa: T201
import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from scripts.deploy.shared_edge_release import (
    EdgeState,
    SharedEdgeReleaseError,
    activate_release,
    rollback_release,
)
from scripts.deploy.shared_edge_smoke import (
    SharedEdgeSmokeError,
    SmokeTarget,
    smoke_both_https_and_redirects,
    smoke_http_no_redirect,
    smoke_https_routes,
)

if TYPE_CHECKING:
    from scripts.deploy.shared_edge_smoke import CurlCallable

ActivateFn = Callable[[str], EdgeState]
RollbackFn = Callable[[], EdgeState]


class CutoverStage(StrEnum):
    """Named cutover stages in activation order."""

    TLS = "tls"
    HTTPS_SMOKE = "https-smoke"
    REDIRECT = "redirect"
    REDIRECT_SMOKE = "redirect-smoke"


class SharedEdgeCutoverError(RuntimeError):
    """Raised when a cutover stage fails."""


@dataclass(frozen=True, slots=True)
class CutoverContext:
    """Inputs for one reversible cutover rehearsal."""

    edge_root: Path
    release_name: str
    smoke_target: SmokeTarget
    curl: CurlCallable
    upstream_network: str = "wef-edge"
    cacert: Path | None = None
    expect_fixture_bodies: bool = True
    reload_callback: Callable[[], None] | None = None
    skip_redirect: bool = False
    activate_fn: ActivateFn | None = None
    rollback_fn: RollbackFn | None = None


@dataclass(slots=True)
class CutoverResult:
    """Outcome of a cutover run, including completed stages."""

    state: EdgeState
    completed_stages: list[CutoverStage] = field(default_factory=list)


def _default_activate(context: CutoverContext, config: str) -> EdgeState:
    return activate_release(
        context.edge_root,
        context.release_name,
        config,
        upstream_network=context.upstream_network,
        reload_callback=context.reload_callback,
    )


def _default_rollback(context: CutoverContext) -> EdgeState:
    state = rollback_release(
        context.edge_root,
        upstream_network=context.upstream_network,
    )
    if context.reload_callback is not None:
        context.reload_callback()
    return state


def run_cutover_stages(context: CutoverContext) -> CutoverResult:
    """Activate TLS, smoke, optionally enable redirects, and roll back on failure.

    Redirect activation is gated: it only runs after both HTTPS routes pass.
    Any later smoke or activation failure restores the previous validated edge
    release through ``rollback_release``.
    """
    activate = context.activate_fn or (lambda config: _default_activate(context, config))
    rollback = context.rollback_fn or (lambda: _default_rollback(context))
    completed: list[CutoverStage] = []
    try:
        state = activate("tls")
        completed.append(CutoverStage.TLS)

        smoke_https_routes(
            context.curl,
            context.smoke_target,
            cacert=context.cacert,
            expect_fixture_bodies=context.expect_fixture_bodies,
        )
        smoke_http_no_redirect(context.curl, context.smoke_target)
        completed.append(CutoverStage.HTTPS_SMOKE)

        if context.skip_redirect:
            return CutoverResult(state=state, completed_stages=completed)

        state = activate("tls-redirect")
        completed.append(CutoverStage.REDIRECT)

        smoke_both_https_and_redirects(
            context.curl,
            context.smoke_target,
            cacert=context.cacert,
            expect_fixture_bodies=context.expect_fixture_bodies,
        )
        completed.append(CutoverStage.REDIRECT_SMOKE)
    except (SharedEdgeReleaseError, SharedEdgeSmokeError) as error:
        if not completed:
            msg = f"cutover failed before any activation: {error}"
            raise SharedEdgeCutoverError(msg) from error
        try:
            rollback()
        except SharedEdgeReleaseError as rollback_error:
            msg = f"cutover failed ({error}); rollback also failed ({rollback_error})"
            raise SharedEdgeCutoverError(msg) from rollback_error
        msg = f"cutover failed after {completed[-1].value}: {error}; rolled back"
        raise SharedEdgeCutoverError(msg) from error
    else:
        return CutoverResult(state=state, completed_stages=completed)


def main(argv: list[str] | None = None) -> int:
    """CLI entry for staged cutover planning; live binding is proof/E7-T10 owned."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edge-root", type=Path, required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--upstream-network", default="wef-edge")
    parser.add_argument("--skip-redirect", action="store_true")
    parser.add_argument(
        "--dry-plan",
        action="store_true",
        help="Print the planned stage order without mutating anything.",
    )
    arguments = parser.parse_args(argv)
    stages = [CutoverStage.TLS, CutoverStage.HTTPS_SMOKE]
    if not arguments.skip_redirect:
        stages.extend([CutoverStage.REDIRECT, CutoverStage.REDIRECT_SMOKE])
    if arguments.dry_plan:
        print("shared_edge_cutover plan: " + " -> ".join(stage.value for stage in stages))
        print(
            f"edge_root={arguments.edge_root} release={arguments.release} "
            f"upstream_network={arguments.upstream_network}"
        )
        return 0
    print(
        "shared_edge_cutover: live execution requires a proof/operator curl binder; "
        "use --dry-plan or scripts.prove_shared_edge_runtime",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
