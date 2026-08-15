"""Constrained source reader and atomic local media object storage."""

from __future__ import annotations

import hashlib
import io
import os
import stat
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from PIL import Image, ImageOps, UnidentifiedImageError

from wef_backend.features.ingestion.domain.media_storage import (
    DerivativeVariant,
    MediaLimits,
    MediaObservation,
    MediaType,
    ObservationReason,
    ObservationStatus,
    PublicDerivative,
    StorageClass,
    StoredObject,
    VerifiedOriginal,
    descriptor_identity,
    opaque_storage_key,
)

if TYPE_CHECKING:
    from wef_backend.features.ingestion.domain.model import MediaDescriptor

_CHUNK_SIZE = 1024 * 1024
_MP4_SIGNATURE_BYTES = 12
_IMAGE_MIME_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}
_VIDEO_MIME_TYPES = {"video/mp4"}
_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "video/mp4": "mp4",
}


@dataclass(frozen=True, slots=True)
class LocalMediaStorage:
    """Verify source files and atomically publish class-separated objects."""

    source_root: Path
    originals_root: Path
    derivatives_root: Path
    limits: MediaLimits = field(default_factory=MediaLimits)

    def observe_and_store(
        self,
        descriptor: MediaDescriptor,
        expected_checksum_sha256: str | None = None,
    ) -> MediaObservation:
        """Reject unsafe metadata/path cases before opening any source bytes."""
        identity = descriptor_identity(descriptor)
        reason, source_path, safe_size = self._pre_read(descriptor)
        if reason is not None:
            status = (
                ObservationStatus.UNREAD_UNAVAILABLE
                if reason is ObservationReason.MISSING
                else ObservationStatus.UNREAD_REJECTED
            )
            return MediaObservation(
                status=status,
                reason=reason,
                descriptor_identity=identity,
                observed_checksum_sha256=None,
                observed_byte_size=safe_size,
            )
        if source_path is None:
            message = "safe media source path was not resolved"
            raise RuntimeError(message)
        return self._read_verify_publish(
            descriptor,
            source_path,
            identity,
            expected_checksum_sha256,
        )

    def create_derivatives(self, original: VerifiedOriginal) -> tuple[PublicDerivative, ...]:
        """Create metadata-free WebP and JPEG thumbnails for verified images."""
        if original.media_type is not MediaType.IMAGE:
            return ()
        source_path = self.originals_root / original.stored_object.storage_key
        try:
            with Image.open(source_path) as opened:
                image = ImageOps.exif_transpose(opened)
                image.load()
                if image.mode not in {"RGB", "L"}:
                    clean = Image.new("RGB", image.size)
                    if "A" in image.getbands():
                        clean.paste(image, mask=image.getchannel("A"))
                    else:
                        clean.paste(image)
                    image = clean
                else:
                    image = image.convert("RGB")
                image.thumbnail((self.limits.thumbnail_width, self.limits.thumbnail_height))
                return (
                    self._publish_derivative(
                        image,
                        original.stored_object.checksum_sha256,
                        DerivativeVariant.THUMBNAIL_WEBP_V1,
                        "WEBP",
                        "image/webp",
                        "webp",
                    ),
                    self._publish_derivative(
                        image,
                        original.stored_object.checksum_sha256,
                        DerivativeVariant.THUMBNAIL_JPEG_V1,
                        "JPEG",
                        "image/jpeg",
                        "jpg",
                    ),
                )
        except (OSError, UnidentifiedImageError) as error:
            raise MediaDerivativeError(ObservationReason.DECODE_FAILED) from error

    def _pre_read(  # noqa: PLR0911
        self,
        descriptor: MediaDescriptor,
    ) -> tuple[ObservationReason | None, Path | None, int | None]:
        """Perform descriptor, confinement, lstat, and size checks only."""
        mime_type = descriptor.mime_type or ""
        if mime_type not in _IMAGE_MIME_FORMATS and mime_type not in _VIDEO_MIME_TYPES:
            return ObservationReason.UNSUPPORTED_DESCRIPTOR, None, descriptor.size_bytes
        raw_path = descriptor.path
        path = PurePosixPath(raw_path)
        if path.is_absolute() or raw_path.startswith(("\\", "/")) or ":" in path.parts[0]:
            return ObservationReason.ABSOLUTE_PATH, None, descriptor.size_bytes
        if ".." in path.parts or not path.parts:
            return ObservationReason.PATH_TRAVERSAL, None, descriptor.size_bytes
        current = self.source_root
        try:
            for part in path.parts:
                current = current / part
                metadata = os.lstat(current)
                if stat.S_ISLNK(metadata.st_mode):
                    return ObservationReason.SYMLINK, None, metadata.st_size
            metadata = os.lstat(current)
        except FileNotFoundError:
            return ObservationReason.MISSING, None, None
        if not stat.S_ISREG(metadata.st_mode):
            return ObservationReason.NON_REGULAR, None, metadata.st_size
        if metadata.st_size > self.limits.max_bytes or (
            descriptor.size_bytes is not None and descriptor.size_bytes > self.limits.max_bytes
        ):
            return ObservationReason.OVERSIZED_METADATA, None, metadata.st_size
        return None, current, metadata.st_size

    def _read_verify_publish(  # noqa: PLR0911
        self,
        descriptor: MediaDescriptor,
        source_path: Path,
        identity: str,
        expected_checksum_sha256: str | None,
    ) -> MediaObservation:
        """Stream/hash to a private temp, validate content, then atomically publish."""
        self.originals_root.mkdir(parents=True, exist_ok=True)
        temp_directory = self.originals_root / ".tmp"
        temp_directory.mkdir(parents=True, exist_ok=True)
        descriptor_mime = descriptor.mime_type or ""
        hasher = hashlib.sha256()
        total = 0
        temp_path: Path | None = None
        try:
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            descriptor_fd = os.open(source_path, flags)
            before = os.fstat(descriptor_fd)
            with (
                os.fdopen(descriptor_fd, "rb", closefd=True) as source,
                tempfile.NamedTemporaryFile(
                    mode="wb",
                    dir=temp_directory,
                    prefix="upload-",
                    delete=False,
                ) as destination,
            ):
                temp_path = Path(destination.name)
                while chunk := source.read(_CHUNK_SIZE):
                    total += len(chunk)
                    if total > self.limits.max_bytes:
                        return self._read_rejection(
                            identity,
                            ObservationReason.OVERSIZED_METADATA,
                            total,
                            temp_path,
                        )
                    hasher.update(chunk)
                    destination.write(chunk)
                destination.flush()
                os.fsync(destination.fileno())
            after_path = os.lstat(source_path)
            if (before.st_dev, before.st_ino, before.st_size) != (
                after_path.st_dev,
                after_path.st_ino,
                after_path.st_size,
            ) or total != before.st_size:
                return self._read_rejection(
                    identity,
                    ObservationReason.CHANGED_DURING_READ,
                    total,
                    temp_path,
                )
            media_type, width, height = self._verify_content(temp_path, descriptor_mime)
            checksum = hasher.hexdigest()
            if expected_checksum_sha256 is not None and checksum != expected_checksum_sha256:
                temp_path.unlink(missing_ok=True)
                temp_path = None
                return MediaObservation(
                    status=ObservationStatus.READ_OBSERVED,
                    reason=ObservationReason.CHECKSUM_MISMATCH,
                    descriptor_identity=identity,
                    observed_checksum_sha256=checksum,
                    observed_byte_size=total,
                    original=None,
                )
            key = opaque_storage_key(
                StorageClass.RESTRICTED_ORIGINAL,
                checksum,
                _EXTENSIONS[descriptor_mime],
            )
            final_path = self.originals_root / key
            final_path.parent.mkdir(parents=True, exist_ok=True)
            if final_path.exists():
                temp_path.unlink(missing_ok=True)
            else:
                try:
                    temp_path.replace(final_path)
                except OSError:
                    return self._read_rejection(
                        identity,
                        ObservationReason.STORAGE_FAILED,
                        total,
                        temp_path,
                    )
            temp_path = None
            stored = StoredObject(
                storage_class=StorageClass.RESTRICTED_ORIGINAL,
                storage_key=key,
                checksum_sha256=checksum,
                mime_type=descriptor_mime,
                byte_size=total,
            )
            original = VerifiedOriginal(
                stored_object=stored,
                media_type=media_type,
                mime_type=descriptor_mime,
                width=width,
                height=height,
                duration_seconds=descriptor.duration_seconds,
            )
            return MediaObservation(
                status=ObservationStatus.READ_OBSERVED,
                reason=ObservationReason.VERIFIED,
                descriptor_identity=identity,
                observed_checksum_sha256=checksum,
                observed_byte_size=total,
                original=original,
            )
        except MediaContentError as error:
            return self._read_rejection(identity, error.reason, total or None, temp_path)
        except (OSError, UnidentifiedImageError, Image.DecompressionBombError):
            return self._read_rejection(
                identity,
                ObservationReason.CORRUPT,
                total or None,
                temp_path,
            )
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def _verify_content(
        self,
        path: Path,
        mime_type: str,
    ) -> tuple[MediaType, int | None, int | None]:
        if mime_type in _VIDEO_MIME_TYPES:
            with path.open("rb") as stream:
                signature = stream.read(_MP4_SIGNATURE_BYTES)
            if len(signature) < _MP4_SIGNATURE_BYTES or signature[4:8] != b"ftyp":
                raise MediaContentError(ObservationReason.SIGNATURE_MISMATCH)
            return MediaType.VIDEO, None, None
        expected_format = _IMAGE_MIME_FORMATS[mime_type]
        with Image.open(path) as image:
            if image.format != expected_format:
                raise MediaContentError(ObservationReason.SIGNATURE_MISMATCH)
            width, height = image.size
            if (
                width > self.limits.max_dimension
                or height > self.limits.max_dimension
                or width * height > self.limits.max_pixels
            ):
                raise MediaContentError(ObservationReason.OVER_PIXEL_LIMIT)
            try:
                image.verify()
            except (OSError, SyntaxError) as error:
                raise MediaContentError(ObservationReason.CORRUPT) from error
        return MediaType.IMAGE, width, height

    def _publish_derivative(  # noqa: PLR0913, PLR0917
        self,
        image: Image.Image,
        source_checksum: str,
        variant: DerivativeVariant,
        image_format: str,
        mime_type: str,
        extension: str,
    ) -> PublicDerivative:
        buffer = io.BytesIO()
        image.save(buffer, format=image_format, quality=85)
        payload = buffer.getvalue()
        checksum = hashlib.sha256(payload).hexdigest()
        key = opaque_storage_key(StorageClass.PUBLIC_DERIVATIVE, checksum, extension)
        final_path = self.derivatives_root / key
        final_path.parent.mkdir(parents=True, exist_ok=True)
        if not final_path.exists():
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=final_path.parent,
                prefix="derivative-",
                delete=False,
            ) as destination:
                temp_path = Path(destination.name)
                destination.write(payload)
                destination.flush()
                os.fsync(destination.fileno())
            try:
                try:
                    temp_path.replace(final_path)
                except OSError as error:
                    raise MediaDerivativeError(ObservationReason.STORAGE_FAILED) from error
            finally:
                temp_path.unlink(missing_ok=True)
        return PublicDerivative(
            stored_object=StoredObject(
                storage_class=StorageClass.PUBLIC_DERIVATIVE,
                storage_key=key,
                checksum_sha256=checksum,
                mime_type=mime_type,
                byte_size=len(payload),
            ),
            variant=variant,
            width=image.width,
            height=image.height,
            source_checksum_sha256=source_checksum,
        )

    @staticmethod
    def _read_rejection(
        identity: str,
        reason: ObservationReason,
        byte_size: int | None,
        temp_path: Path | None,
    ) -> MediaObservation:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        return MediaObservation(
            status=ObservationStatus.UNREAD_REJECTED,
            reason=reason,
            descriptor_identity=identity,
            observed_checksum_sha256=None,
            observed_byte_size=byte_size,
        )


class MediaDerivativeError(RuntimeError):
    """Stable derivative failure without source/storage path disclosure."""

    def __init__(self, reason: ObservationReason) -> None:
        """Store only a stable reason code."""
        self.reason = reason
        super().__init__(f"media derivative failed: {reason.value}")


class MediaContentError(RuntimeError):
    """Stable content validation failure used before object publication."""

    def __init__(self, reason: ObservationReason) -> None:
        """Store only a stable reason code."""
        self.reason = reason
        super().__init__(f"media content rejected: {reason.value}")
