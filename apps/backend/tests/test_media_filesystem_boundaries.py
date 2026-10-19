"""Local storage image modes, file races and atomic derivative failures."""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

from tests.test_media_storage import _descriptor, _storage, _write_jpeg
from wef_backend.features.ingestion.domain.media_storage import (
    MediaLimits,
    MediaType,
    ObservationReason,
    ObservationStatus,
)
from wef_backend.features.ingestion.domain.model import MediaDescriptor, MediaKind
from wef_backend.features.ingestion.infrastructure.media_filesystem import (
    LocalMediaStorage,
    MediaDerivativeError,
)


@pytest.mark.parametrize("mode", ["RGBA", "P"])
def test_derivatives_clean_transparent_and_palette_images(mode: str, tmp_path: Path) -> None:
    """Images with alpha or palettes become metadata-free RGB public thumbnails."""
    storage = _storage(tmp_path)
    source = storage.source_root / "image.png"
    Image.new(mode, (8, 8)).save(source, format="PNG")
    observed = storage.observe_and_store(_descriptor("image.png", mime_type="image/png"))
    assert observed.original is not None
    derivatives = storage.create_derivatives(observed.original)
    assert len(derivatives) == 2
    for derivative in derivatives:
        with Image.open(storage.derivatives_root / derivative.stored_object.storage_key) as image:
            assert image.mode == "RGB"
            assert image.size == (8, 8)
    assert storage.create_derivatives(observed.original) == derivatives


@pytest.mark.parametrize("signature", [b"short", b"0000bad!0000", b"0000ftypisom"])
def test_video_signature_is_verified_and_never_sent_to_image_derivatives(
    signature: bytes, tmp_path: Path
) -> None:
    """Only an MP4 signature produces a verified video object."""
    storage = _storage(tmp_path)
    (storage.source_root / "video.mp4").write_bytes(signature)
    observed = storage.observe_and_store(
        MediaDescriptor(MediaKind.VIDEO, "video.mp4", mime_type="video/mp4")
    )
    if signature == b"0000ftypisom":
        assert observed.original is not None
        assert observed.original.media_type is MediaType.VIDEO
        assert storage.create_derivatives(observed.original) == ()
    else:
        assert observed.reason is ObservationReason.SIGNATURE_MISMATCH
        assert observed.original is None


def test_derivative_decode_failure_preserves_verified_original_identity(tmp_path: Path) -> None:
    """A damaged private object cannot publish partial public derivatives."""
    storage = _storage(tmp_path)
    _write_jpeg(storage.source_root / "photos/example.jpg")
    observed = storage.observe_and_store(_descriptor())
    assert observed.original is not None
    (storage.originals_root / observed.original.stored_object.storage_key).write_bytes(b"damaged")
    with pytest.raises(MediaDerivativeError) as caught:
        storage.create_derivatives(observed.original)
    assert caught.value.reason is ObservationReason.DECODE_FAILED
    assert not storage.derivatives_root.exists()


def test_derivative_publish_failure_has_a_bounded_reason_and_removes_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An atomic public rename failure leaves the restricted original intact."""
    storage = _storage(tmp_path)
    _write_jpeg(storage.source_root / "photos/example.jpg")
    observed = storage.observe_and_store(_descriptor())
    assert observed.original is not None

    def fail(*_args: object) -> None:
        raise OSError

    monkeypatch.setattr(Path, "replace", fail)
    with pytest.raises(MediaDerivativeError) as caught:
        storage.create_derivatives(observed.original)
    assert caught.value.reason is ObservationReason.STORAGE_FAILED
    assert (storage.originals_root / observed.original.stored_object.storage_key).exists()
    assert not tuple(storage.derivatives_root.rglob("derivative-*"))


@pytest.mark.parametrize("race", ["grow_before_read", "grow_after_read", "open_failure"])
def test_streaming_source_races_never_publish_an_unverified_original(
    race: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """File changes after the metadata check are rejected and temporary bytes removed."""
    storage = _storage(tmp_path)
    source = storage.source_root / "photos/example.jpg"
    _write_jpeg(source)
    storage = replace(storage, limits=MediaLimits(max_bytes=source.stat().st_size))
    original_open, original_sync = os.open, os.fsync

    def open_source(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if path == source:
            if race == "open_failure":
                raise OSError
            if race == "grow_before_read":
                with source.open("ab") as changed:
                    changed.write(b"growth")
        return original_open(path, flags, mode, dir_fd=dir_fd)

    def sync(descriptor: int) -> None:
        original_sync(descriptor)
        if race == "grow_after_read":
            with source.open("ab") as changed:
                changed.write(b"growth")

    monkeypatch.setattr(os, "open", open_source)
    monkeypatch.setattr(os, "fsync", sync)
    observed = storage.observe_and_store(_descriptor())
    assert observed.status is ObservationStatus.UNREAD_REJECTED
    expected = {
        "grow_before_read": ObservationReason.OVERSIZED_METADATA,
        "grow_after_read": ObservationReason.CHANGED_DURING_READ,
        "open_failure": ObservationReason.CORRUPT,
    }
    assert observed.reason is expected[race]
    assert observed.original is None
    assert not tuple(storage.originals_root.rglob("upload-*"))


def test_image_verification_failure_is_reported_as_corrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A decoder verification error is never mistaken for a verified image."""
    storage = _storage(tmp_path)
    Image.new("RGB", (8, 8)).save(storage.source_root / "image.png", format="PNG")

    def fail_verify(_self: object) -> None:
        raise SyntaxError

    monkeypatch.setattr(PngImagePlugin.PngImageFile, "verify", fail_verify)
    assert (
        storage.observe_and_store(_descriptor("image.png", mime_type="image/png")).reason
        is ObservationReason.CORRUPT
    )


def test_storage_refuses_a_precheck_that_loses_the_resolved_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A successful precheck must retain a confined source path before reading."""
    monkeypatch.setattr(LocalMediaStorage, "_pre_read", lambda *_args: (None, None, 0))
    with pytest.raises(RuntimeError, match="source path was not resolved"):
        _storage(tmp_path).observe_and_store(_descriptor())
