"""Tests for bounded local operator commands."""

import errno
import json
from pathlib import Path

import pytest

from wef_backend import operator
from wef_backend.operator import UnsafeSourceMountError, inspect_source
from wef_backend.settings import Settings


def test_inspect_source_rejects_missing_directory(tmp_path: Path) -> None:
    """A missing source is rejected before any scan."""
    with pytest.raises(UnsafeSourceMountError, match="does not exist"):
        inspect_source(tmp_path / "missing")


def test_inspect_source_rejects_writable_directory(tmp_path: Path) -> None:
    """A source mount must not permit importer writes."""
    with pytest.raises(UnsafeSourceMountError, match="must be mounted read-only"):
        inspect_source(tmp_path)

    assert not (tmp_path / ".wef-write-probe").exists()


def test_inspect_source_propagates_unexpected_probe_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected filesystem failures are preserved for diagnosis."""
    error = OSError(errno.EIO, "synthetic I/O failure")

    def fail_touch(_self: Path, *, mode: int = 0o666, exist_ok: bool = True) -> None:
        del mode, exist_ok
        raise error

    monkeypatch.setattr(Path, "touch", fail_touch)

    with pytest.raises(OSError, match="synthetic I/O failure") as raised:
        inspect_source(tmp_path)

    assert raised.value is error


@pytest.mark.parametrize("probe_errno", [errno.EACCES, errno.EROFS])
def test_inspect_source_accepts_read_only_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe_errno: int,
) -> None:
    """Expected read-only errors result in bounded metadata."""
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "listing.json").write_text("{}", encoding="utf-8")

    def reject_touch(_self: Path, *, mode: int = 0o666, exist_ok: bool = True) -> None:
        del mode, exist_ok
        raise OSError(probe_errno, "read-only")

    monkeypatch.setattr(Path, "touch", reject_touch)

    assert inspect_source(tmp_path) == operator.SourceInspection(
        file_count=1,
        read_only=True,
        source=str(tmp_path),
    )


def test_main_emits_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The command emits stable machine-readable metadata."""
    expected = operator.SourceInspection(file_count=2, read_only=True, source=str(tmp_path))
    monkeypatch.setattr(operator, "load_settings", lambda: Settings(source_path=tmp_path))
    monkeypatch.setattr(operator, "inspect_source", lambda _source: expected)

    operator.main()

    assert json.loads(capsys.readouterr().out) == {
        "file_count": 2,
        "read_only": True,
        "source": str(tmp_path),
    }
