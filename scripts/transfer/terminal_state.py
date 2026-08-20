"""Terminal-state refusal rules before historical bundle packaging."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TerminalState:
    """Minimal E3-T5 terminal-state snapshot for packaging gates."""

    active_import_lease: bool
    open_geocode_claims: int
    pending_provider_work: int
    reconciliation_complete: bool


def packaging_refusal_reasons(state: TerminalState) -> tuple[str, ...]:
    """Return sorted refusal reasons; empty means packaging may proceed."""
    reasons: list[str] = []
    if state.active_import_lease:
        reasons.append("active_import_lease")
    if state.open_geocode_claims > 0:
        reasons.append("open_geocode_claims")
    if state.pending_provider_work > 0:
        reasons.append("pending_provider_work")
    if not state.reconciliation_complete:
        reasons.append("reconciliation_incomplete")
    return tuple(sorted(reasons))
