"""Provider-neutral geocoding values and review policy."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

NORMALIZER_VERSION = "warsaw-address-v2"
SCOPE_VERSION = "warsaw-scope-v1"
REQUEST_VERSION = "forward-geocode-v2"
REVIEW_POLICY_VERSION = "warsaw-review-v1"

_WHITESPACE = re.compile(r"\s+")
_PUNCTUATION = re.compile(r"\s*[,;|]+\s*")
_STREET_PREFIX = re.compile(
    r"^(?:ul(?:ica)?\.?|вул(?:иця)?\.?|ул(?:ица)?\.?)\s*",
    re.IGNORECASE,
)
_STREET_TOKEN = re.compile(
    r"(?<!\w)(?:ulica|aleja|osiedle|plac|улица|ul|al|os|pl|вул|ул)(?!\w)\.?",
    re.IGNORECASE,
)
_INLINE_STREET_PREFIX = re.compile(
    r"(?<!\w)(?:ul(?:ica)?|вул(?:иця)?|ул(?:ица)?)\.?\s+",
    re.IGNORECASE,
)
_AREA_WORD_PREFIX = re.compile(r"^\s*(?:район|district|dzielnica)\s+", re.IGNORECASE)
_INLINE_AREA_WORD = re.compile(r"(?<!\w)(?:район|district|dzielnica)\s+", re.IGNORECASE)
_AREA_SUFFIX_PARENTHETICAL = re.compile(r"\s*\([^()]*\)\s*$")
_INLINE_PARENTHETICAL = re.compile(r"\s*\([^()]*\)")
_LEADING_DECORATION = re.compile(r"^[\s•·\-\u2013—*]+")
_ADDRESS_SEGMENT_SPLIT = re.compile(r"[,|]")
_CITY_NAMES = re.compile(r"\b(?:warszawa|варшава|варшаві|warsaw)\b", re.IGNORECASE)
# lon/lat order: west, south, east, north — shared with provider request filters.
WARSAW_BOUNDS = (20.28, 51.94, 21.37, 52.37)
_WARSAW_BOUNDS = WARSAW_BOUNDS
WARSAW_BIAS_LON = Decimal("21.0122")
WARSAW_BIAS_LAT = Decimal("52.2297")
_DISTRICTS = {
    "bemowo": "Bemowo",
    "bialoleka": "Białołęka",
    "białołęka": "Białołęka",
    "bielany": "Bielany",
    "mokotow": "Mokotów",
    "mokotów": "Mokotów",
    "ochota": "Ochota",
    "praga-polnoc": "Praga-Północ",
    "praga-północ": "Praga-Północ",
    "praga-poludnie": "Praga-Południe",
    "praga-południe": "Praga-Południe",
    "rembertow": "Rembertów",
    "rembertów": "Rembertów",
    "srodmiescie": "Śródmieście",
    "śródmieście": "Śródmieście",
    "targowek": "Targówek",
    "targówek": "Targówek",
    "ursus": "Ursus",
    "ursynow": "Ursynów",
    "ursynów": "Ursynów",
    "wawer": "Wawer",
    "wesola": "Wesoła",
    "wesoła": "Wesoła",
    "wilanow": "Wilanów",
    "wilanów": "Wilanów",
    "wlochy": "Włochy",
    "włochy": "Włochy",
    "wola": "Wola",
    "zoliborz": "Żoliborz",
    "żoliborz": "Żoliborz",
}
# Reviewed owner reroutes for genuine source variants that exact folding cannot
# fix: hyphen loss and letter typos. Closed list — never fuzzy matching.
_DISTRICT_ALIASES = {
    "białołęcka": "Białołęka",
    "bialolecka": "Białołęka",
    "praga południe": "Praga-Południe",
    "praga poludnie": "Praga-Południe",
    "praga pólnoc": "Praga-Północ",
    "praga polnoc": "Praga-Północ",
}


class GeocodeProvider(StrEnum):
    """Supported provider identities included in durable cache keys."""

    FIXTURE = "fixture"
    GEOAPIFY = "geoapify"
    LOCATIONIQ = "locationiq"
    NOMINATIM = "nominatim"


class GeocodePrecision(StrEnum):
    """Provider-neutral spatial precision."""

    BUILDING = "building"
    STREET = "street"
    DISTRICT = "district"
    CITY = "city"
    UNKNOWN = "unknown"


class GeocodeReviewStatus(StrEnum):
    """Review states shared with canonical locations."""

    ACCEPTED = "accepted"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"
    UNGEOCODED = "ungeocoded"


class GeocodeErrorCode(StrEnum):
    """Bounded provider/cache outcomes safe for persistence and logs."""

    NO_RESULT = "no_result"
    TIMEOUT = "timeout"
    TRANSIENT = "transient"
    QUOTA = "quota"
    POLICY = "policy"
    INVALID_RESPONSE = "invalid_response"


class SelectionReason(StrEnum):
    """Stable reasons for automatic or manual selection transitions."""

    AUTO_PRECISE_IN_SCOPE = "auto_precise_in_scope"
    LOW_CONFIDENCE = "low_confidence"
    LOW_PRECISION = "low_precision"
    OUT_OF_SCOPE = "out_of_scope"
    PROVIDER_ERROR = "provider_error"
    MANUAL_ACCEPT = "manual_accept"
    MANUAL_REJECT = "manual_reject"
    MANUAL_UNRESOLVE = "manual_unresolve"
    AI_ASSISTED_CORRECTION = "ai_assisted_correction"


@dataclass(frozen=True, slots=True)
class NormalizedGeocodeQuery:
    """Versioned normalized query while preserving source display text."""

    original: str
    normalized: str
    district: str | None
    city: str = "Warszawa"
    country_code: str = "PL"

    def __post_init__(self) -> None:
        """Reject empty or invented queries."""
        if not self.original.strip() or not self.normalized:
            message = "geocode query must preserve a non-empty source value"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class GeocodeCacheKey:
    """Complete provider/version/query cache identity."""

    provider: GeocodeProvider
    normalized_query: str
    normalizer_version: str = NORMALIZER_VERSION
    scope_version: str = SCOPE_VERSION
    request_version: str = REQUEST_VERSION

    @property
    def query_hash(self) -> str:
        """Return a stable SHA-256 over every behavior-changing input."""
        payload = json.dumps(
            {
                "normalizer_version": self.normalizer_version,
                "provider": self.provider.value,
                "query": self.normalized_query,
                "request_version": self.request_version,
                "scope_version": self.scope_version,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class GeocodeResult:
    """Sanitized provider-neutral result suitable for durable storage."""

    provider: GeocodeProvider
    provider_result_id: str | None
    longitude: Decimal | None
    latitude: Decimal | None
    display_name: str | None
    precision: GeocodePrecision
    confidence: Decimal
    within_scope: bool | None
    attribution_text: str
    error_code: GeocodeErrorCode | None = None
    diagnostic: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        """Keep coordinate, confidence, and diagnostic surfaces bounded."""
        if not Decimal(0) <= self.confidence <= Decimal(1):
            message = "geocode confidence must be between zero and one"
            raise ValueError(message)
        if (self.longitude is None) != (self.latitude is None):
            message = "geocode coordinates must be both present or both absent"
            raise ValueError(message)
        if self.error_code is not None and self.longitude is not None:
            message = "geocode errors cannot carry a selected coordinate"
            raise ValueError(message)
        if any(
            key.lower() in {"api_key", "key", "token", "authorization"}
            for key, _ in self.diagnostic
        ):
            message = "geocode diagnostics contain a forbidden secret field"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    """Atomic location transition derived independently of provider shape."""

    status: GeocodeReviewStatus
    reason: SelectionReason
    select_result: bool
    out_of_scope: bool


_EMOJI = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "]",
    flags=re.UNICODE,
)
_STREET_LABEL = re.compile(r"^(?:улица|ulica|street)\s*:\s*", re.IGNORECASE)
_NOISE_SEGMENT = re.compile(
    r"(?:"
    r"\d+\s*(?:минут|minutes|min\.?|м\b|metr\w*)|"
    r"трамвай\w*|остановк\w*|"
    r"пешком|do\s+metra|to\s+metro|"
    r"^[\s•·\-\u2013—*]+$"
    r")",
    re.IGNORECASE,
)
_OTHER_CITY = re.compile(r"^[A-Za-zÀ-ž][\w\-']*(?:\s+[A-Za-zÀ-ž][\w\-']*)?$")


def _is_noise_segment(segment: str) -> bool:
    """Return whether one segment is decoration or distance prose only."""
    cleaned = _LEADING_DECORATION.sub("", segment.strip())
    cleaned = _EMOJI.sub("", cleaned).strip()
    if not cleaned:
        return True
    if _NOISE_SEGMENT.search(cleaned) and not _STREET_TOKEN.search(cleaned):
        return warsaw_district_in(cleaned) is None and _extract_other_city(cleaned) is None
    return False


def _format_street_segment(value: str) -> str:
    """Map Cyrillic street labels to Polish-forward `ul.` while preserving tokens."""
    cleaned = unicodedata.normalize("NFKC", value).strip()
    cleaned = _LEADING_DECORATION.sub("", cleaned)
    cleaned = _EMOJI.sub("", cleaned)
    had_label = bool(_STREET_LABEL.search(value))
    cleaned = _STREET_LABEL.sub("", cleaned)
    had_prefix = had_label or bool(
        _STREET_PREFIX.match(cleaned) or _INLINE_STREET_PREFIX.search(cleaned),
    )
    cleaned = _INLINE_STREET_PREFIX.sub("ul. ", cleaned)
    if _STREET_PREFIX.match(cleaned):
        cleaned = _STREET_PREFIX.sub("ul. ", cleaned)
    cleaned = _INLINE_PARENTHETICAL.sub("", cleaned)
    cleaned = _WHITESPACE.sub(" ", cleaned).strip(" ,")
    if had_prefix and not cleaned.casefold().startswith("ul."):
        cleaned = f"ul. {cleaned}"
    return cleaned


def _extract_other_city(segment: str) -> str | None:
    """Return a non-Warsaw city token when one segment names it explicitly."""
    cleaned = _LEADING_DECORATION.sub("", segment.strip())
    cleaned = _AREA_WORD_PREFIX.sub("", cleaned)
    cleaned = _AREA_SUFFIX_PARENTHETICAL.sub("", cleaned)
    cleaned = _WHITESPACE.sub(" ", cleaned).strip(" ,")
    if not cleaned or _STREET_TOKEN.search(cleaned):
        return None
    if warsaw_district_in(cleaned) is not None:
        return None
    if _CITY_NAMES.search(cleaned):
        return "Warszawa"
    if _OTHER_CITY.fullmatch(cleaned):
        return cleaned
    return None


@dataclass(frozen=True, slots=True)
class _ParsedDisplayName:
    """Structured tokens extracted from one source location line."""

    street: str | None
    district: str | None
    city: str | None


def _parse_display_name_segments(
    segments: list[str],
    *,
    original: str,
    district: str | None,
) -> _ParsedDisplayName:
    """Classify comma/pipe segments into street, district, and city tokens."""
    street: str | None = None
    resolved_district = canonical_warsaw_district(district) or warsaw_district_in(original)
    city: str | None = None

    for segment in segments:
        if _is_noise_segment(segment):
            continue
        if _STREET_TOKEN.search(segment):
            candidate = _format_street_segment(segment)
            if candidate:
                street = candidate
            continue
        segment_district = warsaw_district_in(segment)
        if segment_district is not None:
            resolved_district = segment_district
            continue
        segment_city = _extract_other_city(segment)
        if segment_city is not None:
            city = segment_city
            continue
        formatted = _format_street_segment(segment)
        if formatted and _STREET_LABEL.search(segment):
            street = formatted

    return _ParsedDisplayName(
        street=street,
        district=resolved_district,
        city=city,
    )


def _assemble_display_name(parsed: _ParsedDisplayName) -> list[str]:
    """Order extracted tokens as street, district, city with Warsaw defaults."""
    parts: list[str] = []
    if parsed.street:
        parts.append(parsed.street)
    joined = " ".join(parts).casefold()
    if parsed.district and parsed.district.casefold() not in joined:
        parts.append(parsed.district)
        joined = " ".join(parts).casefold()
    if parsed.city and parsed.city.casefold() not in joined:
        parts.append(parsed.city)
    elif parsed.city is None and "warszawa" not in joined and (
        parsed.district is not None or parsed.street is not None
    ):
        parts.append("Warszawa")
    return parts


def normalize_location_display_name(source: str | None, *, district: str | None = None) -> str:
    """Return a Polish-forward display name without changing location identity keys."""
    if not source or not source.strip():
        return "Unknown location"
    original = source.strip()

    value = unicodedata.normalize("NFKC", original)
    value = _LEADING_DECORATION.sub("", value)
    value = _EMOJI.sub("", value)
    segments = [
        segment.strip()
        for segment in _ADDRESS_SEGMENT_SPLIT.split(value)
        if segment.strip()
    ]

    parsed = _parse_display_name_segments(segments, original=original, district=district)
    parts = _assemble_display_name(parsed)
    if parts:
        return ", ".join(parts)
    return " ".join(original.split())


def normalize_geocode_query(source: str, district: str | None = None) -> NormalizedGeocodeQuery:
    """Normalize supported Warsaw forms without replacing the display value."""
    original = source
    value = unicodedata.normalize("NFKC", source).strip()
    value = _LEADING_DECORATION.sub("", value)
    value = _INLINE_STREET_PREFIX.sub("ul. ", value)
    value = _STREET_PREFIX.sub("ul. ", value)
    value = _INLINE_AREA_WORD.sub("", value)
    value = _CITY_NAMES.sub("Warszawa", value)
    value = _INLINE_PARENTHETICAL.sub("", value)
    value = _PUNCTUATION.sub(", ", value)
    value = _WHITESPACE.sub(" ", value).strip(" ,")
    normalized_district = canonical_warsaw_district(district) or warsaw_district_in(original)
    folded = value.casefold()
    if "warszawa" not in folded:
        value = f"{value}, Warszawa"
    if normalized_district is not None and normalized_district.casefold() not in value.casefold():
        value = f"{value}, {normalized_district}"
    value = f"{value}, PL"
    return NormalizedGeocodeQuery(
        original=original,
        normalized=value.casefold(),
        district=normalized_district,
    )


def canonical_warsaw_district(value: str | None) -> str | None:
    """Return a reviewed canonical district name when unambiguous."""
    if value is None:
        return None
    normalized = _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", value)).strip().casefold()
    return _DISTRICTS.get(normalized) or _DISTRICT_ALIASES.get(normalized)


def _district_match_variants() -> dict[str, tuple[str, ...]]:
    """Map each canonical district to itself plus every reviewed stored spelling."""
    variants: dict[str, set[str]] = {}
    for folded, canonical in (*_DISTRICTS.items(), *_DISTRICT_ALIASES.items()):
        spellings = variants.setdefault(canonical, {canonical})
        spellings.add(folded)
        spellings.add(canonical)
    return {canonical: tuple(sorted(spellings)) for canonical, spellings in variants.items()}


_DISTRICT_MATCH_VARIANTS = _district_match_variants()


def district_match_values(value: str) -> tuple[str, ...]:
    """Expand one requested district to every spelling it must match in storage."""
    canonical = canonical_warsaw_district(value)
    if canonical is None:
        return (value,)
    return _DISTRICT_MATCH_VARIANTS.get(canonical, (canonical,))


def warsaw_district_in(value: str) -> str | None:
    """Return the canonical district when one comma/pipe segment names it exactly."""
    for segment in _ADDRESS_SEGMENT_SPLIT.split(value):
        candidate = _AREA_WORD_PREFIX.sub("", segment)
        candidate = _AREA_SUFFIX_PARENTHETICAL.sub("", candidate)
        canonical = canonical_warsaw_district(candidate)
        if canonical is not None:
            return canonical
    return None


def looks_like_warsaw_address(value: str) -> bool:
    """Screen one template line for street, city, or exact district evidence."""
    if _STREET_TOKEN.search(value) is not None or _CITY_NAMES.search(value) is not None:
        return True
    return warsaw_district_in(value) is not None


def within_warsaw(longitude: Decimal, latitude: Decimal) -> bool:
    """Validate coordinate order and the versioned Warsaw bounding box."""
    west, south, east, north = (Decimal(str(item)) for item in _WARSAW_BOUNDS)
    return west <= longitude <= east and south <= latitude <= north


def review_geocode_result(
    result: GeocodeResult,
    *,
    minimum_confidence: Decimal = Decimal("0.80"),
) -> ReviewDecision:
    """Fail closed unless a precise, confident result is within Warsaw."""
    if result.error_code is not None or result.longitude is None or result.latitude is None:
        return ReviewDecision(
            status=GeocodeReviewStatus.UNGEOCODED,
            reason=SelectionReason.PROVIDER_ERROR,
            select_result=False,
            out_of_scope=False,
        )
    in_scope = within_warsaw(result.longitude, result.latitude)
    if result.within_scope is False or not in_scope:
        return ReviewDecision(
            status=GeocodeReviewStatus.NEEDS_REVIEW,
            reason=SelectionReason.OUT_OF_SCOPE,
            select_result=False,
            out_of_scope=True,
        )
    if result.precision not in {GeocodePrecision.BUILDING, GeocodePrecision.STREET}:
        return ReviewDecision(
            status=GeocodeReviewStatus.NEEDS_REVIEW,
            reason=SelectionReason.LOW_PRECISION,
            select_result=False,
            out_of_scope=False,
        )
    if result.confidence < minimum_confidence:
        return ReviewDecision(
            status=GeocodeReviewStatus.NEEDS_REVIEW,
            reason=SelectionReason.LOW_CONFIDENCE,
            select_result=False,
            out_of_scope=False,
        )
    return ReviewDecision(
        status=GeocodeReviewStatus.ACCEPTED,
        reason=SelectionReason.AUTO_PRECISE_IN_SCOPE,
        select_result=True,
        out_of_scope=False,
    )
