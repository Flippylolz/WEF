"""Framework-independent media verification, storage, and replay values."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wef_backend.features.ingestion.domain.model import MediaDescriptor

VERIFIER_VERSION = "media-verify-v1"
STORAGE_KEY_VERSION = "media-object-v1"
TRANSFORM_VERSION = "image-transform-v1"
_SHA256_LENGTH = 64
_MINIMUM_KEY_PARTS = 4
_MAX_EXTENSION_LENGTH = 8


class StorageClass(StrEnum):
    """Security boundary for physically stored bytes."""

    RESTRICTED_ORIGINAL = "restricted_original"
    PUBLIC_DERIVATIVE = "public_derivative"


class MediaType(StrEnum):
    """Verified media families."""

    IMAGE = "image"
    VIDEO = "video"


class ObservationStatus(StrEnum):
    """Whether bytes were safely opened and observed."""

    READ_OBSERVED = "read_observed"
    UNREAD_UNAVAILABLE = "unread_unavailable"
    UNREAD_REJECTED = "unread_rejected"


class ObservationReason(StrEnum):
    """Versioned pre-read and content-verification outcomes."""

    VERIFIED = "verified"
    MISSING = "missing"
    ABSOLUTE_PATH = "absolute_path"
    PATH_TRAVERSAL = "path_traversal"
    SYMLINK = "symlink"
    NON_REGULAR = "non_regular"
    OVERSIZED_METADATA = "oversized_metadata"
    UNSUPPORTED_DESCRIPTOR = "unsupported_descriptor"
    CHANGED_DURING_READ = "changed_during_read"
    SIGNATURE_MISMATCH = "signature_mismatch"
    CORRUPT = "corrupt"
    OVER_PIXEL_LIMIT = "over_pixel_limit"
    DECODE_FAILED = "decode_failed"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    STORAGE_FAILED = "storage_failed"


class OriginalDisposition(StrEnum):
    """Stable expected-media outcomes."""

    STORED = "stored"
    MISSING = "missing"
    REJECTED = "rejected"
    UNSUPPORTED = "unsupported"
    UNASSOCIATED = "unassociated"


class DerivativeStatus(StrEnum):
    """Independent derivative-attempt states."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class DerivativeVariant(StrEnum):
    """Public versioned derivative variants."""

    THUMBNAIL_WEBP_V1 = "thumbnail_webp_v1"
    THUMBNAIL_JPEG_V1 = "thumbnail_jpeg_v1"


@dataclass(frozen=True, slots=True)
class StoredObject:
    """Verified object published atomically under an opaque key."""

    storage_class: StorageClass
    storage_key: str
    checksum_sha256: str
    mime_type: str
    byte_size: int

    def __post_init__(self) -> None:
        """Reject paths, invalid hashes, and impossible sizes."""
        if len(self.checksum_sha256) != _SHA256_LENGTH or self.byte_size < 0:
            message = "stored media object requires a SHA-256 and non-negative size"
            raise ValueError(message)
        path = PurePosixPath(self.storage_key)
        if path.is_absolute() or ".." in path.parts or len(path.parts) < _MINIMUM_KEY_PARTS:
            message = "stored media key must be opaque and versioned"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class VerifiedOriginal:
    """Safely observed original plus metadata needed for persistence."""

    stored_object: StoredObject
    media_type: MediaType
    mime_type: str
    width: int | None
    height: int | None
    duration_seconds: int | None


@dataclass(frozen=True, slots=True)
class PublicDerivative:
    """Metadata-free derivative pinned to one original checksum."""

    stored_object: StoredObject
    variant: DerivativeVariant
    width: int
    height: int
    source_checksum_sha256: str


@dataclass(frozen=True, slots=True)
class MediaObservation:
    """One read or pre-read outcome with deterministic replay identity."""

    status: ObservationStatus
    reason: ObservationReason
    descriptor_identity: str
    observed_checksum_sha256: str | None
    observed_byte_size: int | None
    original: VerifiedOriginal | None = None

    def __post_init__(self) -> None:
        """Keep unread and safely read shapes disjoint."""
        read = self.status is ObservationStatus.READ_OBSERVED
        if read != (self.observed_checksum_sha256 is not None):
            message = "only safely read observations carry a checksum"
            raise ValueError(message)
        if self.original is not None and not read:
            message = "only safely read observations carry a stored original"
            raise ValueError(message)
        if (self.original is not None) != (self.reason is ObservationReason.VERIFIED):
            message = "only verified observations carry a stored original"
            raise ValueError(message)
        if not read and self.reason in {
            ObservationReason.VERIFIED,
            ObservationReason.CHECKSUM_MISMATCH,
        }:
            message = "unread media requires a pre-read rejection or unavailable reason"
            raise ValueError(message)

    @property
    def content_identity(self) -> str:
        """Return checksum or a stable unread sentinel for replay keys."""
        if self.observed_checksum_sha256 is not None:
            return self.observed_checksum_sha256
        return f"unread:{self.reason.value}"


@dataclass(frozen=True, slots=True)
class MediaLimits:
    """Resource limits applied before and during decode."""

    max_bytes: int = 50 * 1024 * 1024
    max_pixels: int = 40_000_000
    max_dimension: int = 16_384
    thumbnail_width: int = 1280
    thumbnail_height: int = 1280

    def __post_init__(self) -> None:
        """Require useful positive bounded limits."""
        values = (
            self.max_bytes,
            self.max_pixels,
            self.max_dimension,
            self.thumbnail_width,
            self.thumbnail_height,
        )
        if any(value <= 0 for value in values):
            message = "media limits must be positive"
            raise ValueError(message)


def descriptor_identity(descriptor: MediaDescriptor) -> str:
    """Hash descriptor metadata without exposing a source path in persistence."""
    payload = json.dumps(
        {
            "duration_seconds": descriptor.duration_seconds,
            "height": descriptor.height,
            "kind": descriptor.kind.value,
            "mime_type": descriptor.mime_type,
            "path": descriptor.path,
            "size_bytes": descriptor.size_bytes,
            "width": descriptor.width,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def opaque_storage_key(
    storage_class: StorageClass,
    checksum_sha256: str,
    extension: str,
) -> str:
    """Create a non-source-derived versioned key within one storage class."""
    if len(checksum_sha256) != _SHA256_LENGTH or any(
        char not in "0123456789abcdef" for char in checksum_sha256
    ):
        message = "opaque media key requires a lowercase SHA-256"
        raise ValueError(message)
    safe_extension = extension.casefold().lstrip(".")
    if not safe_extension.isalnum() or len(safe_extension) > _MAX_EXTENSION_LENGTH:
        message = "opaque media key extension is invalid"
        raise ValueError(message)
    return (
        f"{STORAGE_KEY_VERSION}/{storage_class.value}/"
        f"{checksum_sha256[:2]}/{checksum_sha256[2:4]}/{checksum_sha256}.{safe_extension}"
    )
