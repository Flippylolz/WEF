"""Safe media verification, atomic storage, derivatives, and orchestration tests."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy.exc import SQLAlchemyError

from wef_backend.features.ingestion.application.media_storage import (
    MediaProcessResult,
    MediaWorkItem,
    ProcessMedia,
)
from wef_backend.features.ingestion.domain.media_grouping import MediaAssociationRule
from wef_backend.features.ingestion.domain.media_storage import (
    DerivativeVariant,
    MediaLimits,
    MediaObservation,
    MediaType,
    ObservationReason,
    ObservationStatus,
    OriginalDisposition,
    PublicDerivative,
    StorageClass,
    StoredObject,
    VerifiedOriginal,
    descriptor_identity,
    opaque_storage_key,
)
from wef_backend.features.ingestion.domain.model import MediaDescriptor, MediaKind
from wef_backend.features.ingestion.infrastructure.media_filesystem import LocalMediaStorage
from wef_backend.features.ingestion.infrastructure.media_repository import (
    MediaPersistenceError,
    SQLAlchemyMediaRepository,
)


def _descriptor(
    path: str = "photos/example.jpg",
    *,
    mime_type: str = "image/jpeg",
    size_bytes: int | None = None,
) -> MediaDescriptor:
    return MediaDescriptor(
        kind=MediaKind.PHOTO,
        path=path,
        mime_type=mime_type,
        size_bytes=size_bytes,
    )


def _storage(tmp_path: Path, *, limits: MediaLimits | None = None) -> LocalMediaStorage:
    source = tmp_path / "source"
    source.mkdir(exist_ok=True)
    return LocalMediaStorage(
        source_root=source,
        originals_root=tmp_path / "originals",
        derivatives_root=tmp_path / "public",
        limits=limits or MediaLimits(),
    )


def _write_jpeg(path: Path, *, color: str = "red", orientation: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (40, 80), color=color)
    exif = image.getexif()
    if orientation is not None:
        exif[274] = orientation
        exif[270] = "private comment"
    image.save(path, format="JPEG", exif=exif)


def test_descriptor_and_opaque_keys_are_stable_without_source_path_leakage() -> None:
    """Replay identity covers descriptor metadata and storage keys use only hashes."""
    first = _descriptor("private/user/photo.jpg", size_bytes=10)
    second = _descriptor("private/user/photo.jpg", size_bytes=11)
    assert descriptor_identity(first) != descriptor_identity(second)
    checksum = "a" * 64
    key = opaque_storage_key(StorageClass.RESTRICTED_ORIGINAL, checksum, ".jpg")
    assert "private" not in key
    assert key.endswith(f"/{checksum}.jpg")
    with pytest.raises(ValueError, match="SHA-256"):
        opaque_storage_key(StorageClass.PUBLIC_DERIVATIVE, "bad", "jpg")
    with pytest.raises(ValueError, match="extension"):
        opaque_storage_key(StorageClass.PUBLIC_DERIVATIVE, checksum, "../jpg")


def test_media_value_invariants_reject_invalid_shapes() -> None:
    """Read/unread and stored-object values cannot represent contradictory state."""
    with pytest.raises(ValueError, match="non-negative"):
        StoredObject(StorageClass.RESTRICTED_ORIGINAL, "v1/a/b/c", "x" * 64, "x", -1)
    with pytest.raises(ValueError, match="opaque"):
        StoredObject(StorageClass.RESTRICTED_ORIGINAL, "../source.jpg", "a" * 64, "x", 1)
    with pytest.raises(ValueError, match="only safely read"):
        MediaObservation(
            ObservationStatus.UNREAD_REJECTED,
            ObservationReason.MISSING,
            "a" * 64,
            "b" * 64,
            1,
        )
    with pytest.raises(ValueError, match="positive"):
        MediaLimits(max_bytes=0)


@pytest.mark.parametrize(
    ("descriptor", "setup", "reason"),
    [
        (_descriptor("/etc/passwd"), "none", ObservationReason.ABSOLUTE_PATH),
        (_descriptor("../secret.jpg"), "none", ObservationReason.PATH_TRAVERSAL),
        (_descriptor("missing.jpg"), "none", ObservationReason.MISSING),
        (_descriptor("folder"), "directory", ObservationReason.NON_REGULAR),
        (_descriptor("link.jpg"), "symlink", ObservationReason.SYMLINK),
        (_descriptor("huge.jpg", size_bytes=999), "file", ObservationReason.OVERSIZED_METADATA),
        (
            _descriptor("unknown.bin", mime_type="application/octet-stream"),
            "file",
            ObservationReason.UNSUPPORTED_DESCRIPTOR,
        ),
    ],
)
def test_pre_read_rejections_never_open_or_hash_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    descriptor: MediaDescriptor,
    setup: str,
    reason: ObservationReason,
) -> None:
    """Unsafe paths/types/metadata persist an unread reason without opening bytes."""
    storage = _storage(tmp_path, limits=MediaLimits(max_bytes=100))
    target = storage.source_root / descriptor.path
    if setup == "directory":
        target.mkdir(parents=True)
    elif setup == "symlink":
        outside = tmp_path / "outside.jpg"
        outside.write_bytes(b"private")
        target.symlink_to(outside)
    elif setup == "file":
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"private")

    def deny_open(*_args: object, **_kwargs: object) -> int:
        message = "unsafe media bytes were opened"
        raise AssertionError(message)

    monkeypatch.setattr(os, "open", deny_open)
    observed = storage.observe_and_store(descriptor)
    assert observed.reason is reason
    assert observed.observed_checksum_sha256 is None
    assert observed.original is None
    assert observed.content_identity == f"unread:{reason.value}"


def test_safe_image_is_streamed_atomically_and_derivatives_strip_metadata(tmp_path: Path) -> None:
    """Verified originals stay restricted and bounded public thumbnails contain no EXIF."""
    storage = _storage(tmp_path)
    source = storage.source_root / "photos/example.jpg"
    _write_jpeg(source, orientation=6)
    observed = storage.observe_and_store(_descriptor(size_bytes=source.stat().st_size))
    assert observed.status is ObservationStatus.READ_OBSERVED
    assert observed.reason is ObservationReason.VERIFIED
    assert observed.original is not None
    original = observed.original
    assert original.stored_object.storage_class is StorageClass.RESTRICTED_ORIGINAL
    assert "example" not in original.stored_object.storage_key
    original_path = storage.originals_root / original.stored_object.storage_key
    assert original_path.read_bytes() == source.read_bytes()
    assert not tuple((storage.originals_root / ".tmp").glob("*"))

    derivatives = storage.create_derivatives(original)
    assert {item.variant for item in derivatives} == set(DerivativeVariant)
    for derivative in derivatives:
        assert derivative.stored_object.storage_class is StorageClass.PUBLIC_DERIVATIVE
        assert derivative.source_checksum_sha256 == observed.observed_checksum_sha256
        public_path = storage.derivatives_root / derivative.stored_object.storage_key
        with Image.open(public_path) as public:
            assert public.size == (80, 40)
            assert not public.getexif()
            assert {str(key).casefold() for key in public.info}.isdisjoint(
                {"exif", "gps", "xmp", "comment"}
            )


def test_replay_deduplicates_bytes_and_replacement_changes_content_identity(tmp_path: Path) -> None:
    """Equal bytes reuse opaque objects while changed bytes produce a new checksum/key."""
    storage = _storage(tmp_path)
    source = storage.source_root / "photos/example.jpg"
    _write_jpeg(source, color="red")
    first = storage.observe_and_store(_descriptor())
    replay = storage.observe_and_store(_descriptor())
    assert first.observed_checksum_sha256 == replay.observed_checksum_sha256
    assert first.original == replay.original
    assert len(tuple(storage.originals_root.rglob("*.jpg"))) == 1
    _write_jpeg(source, color="blue")
    changed = storage.observe_and_store(_descriptor())
    assert changed.observed_checksum_sha256 != first.observed_checksum_sha256
    assert changed.content_identity != first.content_identity
    assert len(tuple(storage.originals_root.rglob("*.jpg"))) == 2


def test_signature_pixel_and_storage_failures_have_stable_reasons(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MIME mismatch, dimension limits, and atomic publish failures stay reportable."""
    storage = _storage(tmp_path)
    source = storage.source_root / "photos/example.jpg"
    source.parent.mkdir(parents=True)
    Image.new("RGB", (10, 10)).save(source, format="PNG")
    assert storage.observe_and_store(_descriptor()).reason is ObservationReason.SIGNATURE_MISMATCH

    _write_jpeg(source)
    limited = _storage(tmp_path, limits=MediaLimits(max_dimension=20))
    assert limited.observe_and_store(_descriptor()).reason is ObservationReason.OVER_PIXEL_LIMIT

    normal = _storage(tmp_path)
    mismatch = normal.observe_and_store(_descriptor(), "b" * 64)
    assert mismatch.status is ObservationStatus.READ_OBSERVED
    assert mismatch.reason is ObservationReason.CHECKSUM_MISMATCH
    assert mismatch.observed_checksum_sha256 is not None
    assert mismatch.original is None
    monkeypatch.setattr(
        Path,
        "replace",
        lambda *_args: (_ for _ in ()).throw(OSError("disk full")),
    )
    assert normal.observe_and_store(_descriptor()).reason is ObservationReason.STORAGE_FAILED
    assert not tuple(normal.originals_root.rglob("upload-*"))


@dataclass
class FakeFilesystem:
    """Scripted filesystem boundary for application disposition tests."""

    observation: MediaObservation
    derivatives: tuple[PublicDerivative, ...] = ()
    failure: RuntimeError | None = None

    def observe_and_store(
        self,
        _: MediaDescriptor,
        expected_checksum_sha256: str | None = None,
    ) -> MediaObservation:
        """Return the scripted observation."""
        del expected_checksum_sha256
        return self.observation

    def create_derivatives(self, _: object) -> tuple[PublicDerivative, ...]:
        """Return or fail the scripted derivative result."""
        if self.failure is not None:
            raise self.failure
        return self.derivatives


@dataclass
class FakeRepository:
    """Capture application persistence inputs."""

    replayed: bool = False
    calls: list[dict[str, object]] = field(default_factory=list)

    async def persist_media_result(self, **values: object) -> bool:
        """Capture the result and return scripted replay state."""
        self.calls.append(values)
        return self.replayed


def _unread(reason: ObservationReason) -> MediaObservation:
    status = (
        ObservationStatus.UNREAD_UNAVAILABLE
        if reason is ObservationReason.MISSING
        else ObservationStatus.UNREAD_REJECTED
    )
    return MediaObservation(status, reason, "a" * 64, None, None)


def _work(*, associated: bool = True) -> MediaWorkItem:
    return MediaWorkItem(
        source_message_id=uuid4(),
        source_message_revision_id=uuid4(),
        source_ordinal=3,
        descriptor=_descriptor(),
        association_version="e2-media-v1",
        offer_id=uuid4() if associated else None,
        association_rule=MediaAssociationRule.EXPLICIT_GROUP if associated else None,
        association_confidence=0.95 if associated else None,
    )


@pytest.mark.parametrize(
    ("reason", "disposition"),
    [
        (ObservationReason.MISSING, OriginalDisposition.MISSING),
        (ObservationReason.UNSUPPORTED_DESCRIPTOR, OriginalDisposition.UNSUPPORTED),
        (ObservationReason.PATH_TRAVERSAL, OriginalDisposition.REJECTED),
    ],
)
async def test_application_persists_unread_dispositions_and_ordinals(
    reason: ObservationReason,
    disposition: OriginalDisposition,
) -> None:
    """Every expected item, including unread outcomes, reaches durable persistence."""
    repository = FakeRepository()
    result = await ProcessMedia(FakeFilesystem(_unread(reason)), repository)(_work())
    assert result.disposition is disposition
    assert repository.calls[0]["disposition"] is disposition
    persisted_item = cast("MediaWorkItem", repository.calls[0]["item"])
    assert persisted_item.source_ordinal == 3


async def test_unassociated_outcome_and_derivative_failure_remain_independent() -> None:
    """Association and derivative failure never erase a safely stored original."""
    storage_object = StoredObject(
        StorageClass.RESTRICTED_ORIGINAL,
        "media-object-v1/restricted_original/aa/bb/" + "a" * 64 + ".jpg",
        "a" * 64,
        "image/jpeg",
        10,
    )
    original = VerifiedOriginal(storage_object, MediaType.IMAGE, "image/jpeg", 10, 10, None)
    observation = MediaObservation(
        ObservationStatus.READ_OBSERVED,
        ObservationReason.VERIFIED,
        "b" * 64,
        "a" * 64,
        10,
        original,
    )

    class FailureError(RuntimeError):
        reason = ObservationReason.DECODE_FAILED

    repository = FakeRepository(replayed=True)
    result: MediaProcessResult = await ProcessMedia(
        FakeFilesystem(observation, failure=FailureError()),
        repository,
    )(_work(associated=False))
    assert result.disposition is OriginalDisposition.UNASSOCIATED
    assert result.derivative_failure is ObservationReason.DECODE_FAILED
    assert result.observation.original is original
    assert result.replayed


async def test_concurrent_media_work_serializes_repository_writes() -> None:
    """Threaded verification retains one ordered database reconciliation boundary."""

    class ContendedRepository:
        def __init__(self) -> None:
            self.active = 0
            self.maximum_active = 0

        async def persist_media_result(self, **_: object) -> bool:
            self.active += 1
            self.maximum_active = max(self.maximum_active, self.active)
            await asyncio.sleep(0.01)
            self.active -= 1
            return False

    repository = ContendedRepository()
    processor = ProcessMedia(
        FakeFilesystem(_unread(ObservationReason.MISSING)),
        repository,
        persistence_lock=asyncio.Lock(),
    )
    await asyncio.gather(*(processor(_work()) for _ in range(4)))
    assert repository.maximum_active == 1


def test_work_item_rejects_invalid_association_and_ordinal() -> None:
    """E2 ordinals and association evidence cannot be partially represented."""
    with pytest.raises(ValueError, match="non-negative"):
        MediaWorkItem(uuid4(), uuid4(), -1, _descriptor(), "v1")
    with pytest.raises(ValueError, match="complete"):
        MediaWorkItem(uuid4(), uuid4(), 0, _descriptor(), "v1", offer_id=uuid4())
    with pytest.raises(ValueError, match="between"):
        MediaWorkItem(
            uuid4(),
            uuid4(),
            0,
            _descriptor(),
            "v1",
            offer_id=uuid4(),
            association_rule=MediaAssociationRule.SAME_MESSAGE,
            association_confidence=2,
        )
    with pytest.raises(ValueError, match="checksum"):
        MediaWorkItem(
            uuid4(),
            uuid4(),
            0,
            _descriptor(),
            "v1",
            expected_checksum_sha256="bad",
        )


async def test_database_failure_reports_only_opaque_orphan_keys() -> None:
    """A post-publication database failure yields bounded cleanup evidence."""
    stored = StoredObject(
        StorageClass.RESTRICTED_ORIGINAL,
        "media-object-v1/restricted_original/aa/bb/" + "a" * 64 + ".jpg",
        "a" * 64,
        "image/jpeg",
        10,
    )
    original = VerifiedOriginal(stored, MediaType.IMAGE, "image/jpeg", 10, 10, None)
    observation = MediaObservation(
        ObservationStatus.READ_OBSERVED,
        ObservationReason.VERIFIED,
        "b" * 64,
        "a" * 64,
        10,
        original,
    )

    class FailingSessionContext:
        async def __aenter__(self) -> object:
            message = "database unavailable"
            raise SQLAlchemyError(message)

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            traceback: object,
        ) -> None:
            del exc_type, exc, traceback

    class FailingFactory:
        def __call__(self) -> FailingSessionContext:
            return FailingSessionContext()

    repository = SQLAlchemyMediaRepository(cast("Any", FailingFactory()))
    with pytest.raises(MediaPersistenceError) as raised:
        await repository.persist_media_result(
            item=_work(associated=False),
            observation=observation,
            disposition=OriginalDisposition.UNASSOCIATED,
            derivatives=(),
            derivative_failure=None,
        )
    assert raised.value.orphaned_keys == (stored.storage_key,)
    assert "source" not in str(raised.value)
