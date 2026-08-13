"""Atomic JSON and Markdown writers for aggregate E2 dry-run reports."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from datetime import datetime

    from wef_backend.features.ingestion.domain import CountBucket, DryRunReport


class ReportWriteError(RuntimeError):
    """Report output failed without exposing an internal destination path."""

    def __init__(self) -> None:
        """Use one stable redacted error message."""
        super().__init__("dry-run report write failed")


@dataclass(frozen=True, slots=True)
class ReportPaths:
    """Internal paths returned to composition code, never report content."""

    json_path: Path
    markdown_path: Path


class AtomicReportWriter:
    """Render both report formats before atomically replacing each target."""

    def __init__(
        self,
        destination: Path,
        *,
        replace: Callable[[Path, Path], None] | None = None,
    ) -> None:
        """Configure an extension-neutral report destination."""
        self._destination = destination
        self._replace = replace or os.replace

    def write(self, report: DryRunReport) -> ReportPaths:
        """Write deterministic JSON and Markdown without partial target files."""
        json_path = self._destination.with_suffix(".json")
        markdown_path = self._destination.with_suffix(".md")
        temporary_paths: list[Path] = []
        try:
            json_bytes = _json_bytes(report)
            markdown_bytes = _markdown(report).encode()
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_temporary = _write_temporary(json_path.parent, json_bytes)
            temporary_paths.append(json_temporary)
            markdown_temporary = _write_temporary(markdown_path.parent, markdown_bytes)
            temporary_paths.append(markdown_temporary)
            self._replace(json_temporary, json_path)
            temporary_paths.remove(json_temporary)
            self._replace(markdown_temporary, markdown_path)
            temporary_paths.remove(markdown_temporary)
        except OSError as error:
            for path in temporary_paths:
                path.unlink(missing_ok=True)
            raise ReportWriteError from error
        return ReportPaths(json_path=json_path, markdown_path=markdown_path)


def report_document(report: DryRunReport) -> Mapping[str, object]:
    """Return the stable machine-report document without sensitive samples."""
    source = None
    if report.source is not None:
        source = {
            "platform": report.source.platform,
            "channel_id": report.source.channel_id,
            "channel_type": report.source.channel_type,
            "file_size": report.source.file_size,
            "checksum": report.source.checksum,
            "published_from": _isoformat(report.source.published_from),
            "published_to": _isoformat(report.source.published_to),
        }
    return {
        "schema": report.report_version,
        "parser_version": report.parser_version,
        "grouping_version": report.grouping_version,
        "terminal_status": report.terminal_status.value,
        "error_code": report.error_code.value if report.error_code is not None else None,
        "source": source,
        "counts": asdict(report.counts),
        "buckets": {
            "source_classifications": _bucket_document(report.source_classifications),
            "candidate_reasons": _bucket_document(report.candidate_reasons),
            "content_types": _bucket_document(report.content_types),
            "extracted_fields": _bucket_document(report.extracted_fields),
            "warning_codes": _bucket_document(report.warning_codes),
            "media_rules": _bucket_document(report.media_rules),
            "unassociated_media_reasons": _bucket_document(report.unassociated_media_reasons),
        },
        "timings_ms": {timing.stage: timing.duration_ms for timing in report.timings},
    }


def _json_bytes(report: DryRunReport) -> bytes:
    rendered = json.dumps(
        report_document(report),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    return f"{rendered}\n".encode()


def _markdown(report: DryRunReport) -> str:
    source = report.source
    source_lines = (
        [
            f"- Platform: `{source.platform}`",
            f"- Channel ID: `{source.channel_id}`",
            f"- Channel type: `{source.channel_type}`",
            f"- File size: `{source.file_size}`",
            f"- SHA-256: `{source.checksum or 'unavailable'}`",
            (
                f"- Published range: `{_isoformat(source.published_from) or 'unavailable'}`"
                f" to `{_isoformat(source.published_to) or 'unavailable'}`"
            ),
        ]
        if source is not None
        else ["- Source metadata: unavailable"]
    )
    sections = [
        "# E2 Historical Parser Dry Run",
        "",
        f"- Status: `{report.terminal_status.value}`",
        f"- Error code: `{report.error_code.value if report.error_code else 'none'}`",
        f"- Parser: `{report.parser_version}`",
        f"- Grouping: `{report.grouping_version}`",
        f"- Report schema: `{report.report_version}`",
        "",
        "## Source",
        "",
        *source_lines,
        "",
        "## Reconciled counts",
        "",
        *(f"- {name}: `{value}`" for name, value in sorted(asdict(report.counts).items())),
        "",
        "## Buckets",
        "",
        *_markdown_buckets("Source classifications", report.source_classifications),
        *_markdown_buckets("Candidate reasons", report.candidate_reasons),
        *_markdown_buckets("Content types", report.content_types),
        *_markdown_buckets("Extracted fields", report.extracted_fields),
        *_markdown_buckets("Warnings", report.warning_codes),
        *_markdown_buckets("Media rules", report.media_rules),
        *_markdown_buckets(
            "Unassociated media reasons",
            report.unassociated_media_reasons,
        ),
        "## Timings",
        "",
        *(f"- {timing.stage}: `{timing.duration_ms} ms`" for timing in report.timings),
        "",
    ]
    return "\n".join(sections)


def _bucket_document(buckets: tuple[CountBucket, ...]) -> dict[str, int]:
    return {bucket.name: bucket.count for bucket in buckets}


def _markdown_buckets(
    title: str,
    buckets: tuple[CountBucket, ...],
) -> list[str]:
    lines = [f"### {title}", ""]
    lines.extend(
        (f"- {bucket.name}: `{bucket.count}`" for bucket in buckets) if buckets else ("- none",)
    )
    lines.append("")
    return lines


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _write_temporary(parent: Path, payload: bytes) -> Path:
    descriptor, name = tempfile.mkstemp(prefix=".e2-report-", dir=parent)
    path = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        path.unlink(missing_ok=True)
        raise
    return path
