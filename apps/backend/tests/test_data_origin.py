"""Unit tests for public offer data-origin derivation."""

from wef_backend.features.catalog.application.data_origin import derive_data_origin


def test_derive_data_origin_without_active_ai() -> None:
    """Parser-only offers stay parser-origin."""
    assert derive_data_origin(has_active_ai_origin=False) == "parser"


def test_derive_data_origin_with_active_ai() -> None:
    """Active AI origins surface the coarse ai_assisted label."""
    assert derive_data_origin(has_active_ai_origin=True) == "ai_assisted"
