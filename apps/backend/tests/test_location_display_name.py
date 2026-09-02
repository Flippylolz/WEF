"""Unit tests for Polish-forward location display-name normalization."""

from __future__ import annotations

from wef_backend.features.ingestion.application.persistence import (
    normalize_location_text,
    normalized_location_key,
)
from wef_backend.features.ingestion.domain.geocoding import normalize_location_display_name


def test_cyrillic_pipe_template_maps_to_street_district_warszawa() -> None:
    """Measured Telegram templates normalize to street, district, Warszawa."""
    assert (
        normalize_location_display_name("ул. Dziekońskiego | Warszawa, Mokotów")
        == "ul. Dziekońskiego, Mokotów, Warszawa"
    )


def test_street_label_maps_to_ul_prefix() -> None:
    """Cyrillic street labels drop decoration and keep Latin street tokens."""
    assert normalize_location_display_name("Улица: Habicha 9") == "ul. Habicha 9, Warszawa"


def test_district_prefix_maps_into_district_position() -> None:
    """Район segments contribute the canonical Warsaw district."""
    assert (
        normalize_location_display_name("Район Bemowo, ул. Powstańców Śląskich")
        == "ul. Powstańców Śląskich, Bemowo, Warszawa"
    )


def test_reorders_bielany_template_to_street_first() -> None:
    """District/city decoration is reordered behind the street token."""
    assert (
        normalize_location_display_name("Bielany | Варшава | ul. Rudnickiego 4")
        == "ul. Rudnickiego 4, Bielany, Warszawa"
    )


def test_near_suburb_keeps_non_warsaw_city() -> None:
    """Neighboring-town offers stay visible without forcing Warszawa."""
    assert (
        normalize_location_display_name("Pruszków, ul. Powstańców Śląskich")
        == "ul. Powstańców Śląskich, Pruszków"
    )
    assert (
        normalize_location_display_name("ул. Jasińskiego | Piaseczno")
        == "ul. Jasińskiego, Piaseczno"
    )


def test_fragment_segment_dropped_when_street_remains() -> None:
    """Bullet/distance fragments do not replace a usable street token."""
    assert (
        normalize_location_display_name("ul. Marszałkowska 1 | • 10 минут до метро")
        == "ul. Marszałkowska 1, Warszawa"
    )


def test_parser_district_hint_is_used_when_missing_from_line() -> None:
    """Extracted district metadata fills gaps in the source location line."""
    assert (
        normalize_location_display_name("ул. Example 10", district="Wola")
        == "ul. Example 10, Wola, Warszawa"
    )


def test_clean_polish_line_only_collapses_whitespace() -> None:
    """Already Latin/Polish lines stay unchanged aside from whitespace."""
    original = "  ul.   Przykładowa 5,  Mokotów,  Warszawa  "
    assert normalize_location_text(original) == "ul. Przykładowa 5, Mokotów, Warszawa"


def test_location_hash_ignores_display_normalization() -> None:
    """Identity keys continue to hash the parsed source line, not display text."""
    raw = "ул. Dziekońskiego | Warszawa, Mokotów"
    assert normalized_location_key(raw) == normalized_location_key(
        "ул. dziekońskiego | warszawa, mokotów",
    )
    assert normalize_location_text(raw) != raw


def test_empty_location_falls_back_to_unknown() -> None:
    """Missing parsed locations keep the existing unknown placeholder."""
    assert normalize_location_text(None) == "Unknown location"
    assert normalize_location_text("   ") == "Unknown location"
