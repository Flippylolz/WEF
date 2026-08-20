"""Unit tests for post-activation inventory path validation."""

# ruff: noqa: D101, D102, PT027

from __future__ import annotations

import unittest
from typing import cast

from scripts.deploy.compare_server_inventory import (
    EXPECTED_WEF_PATHS,
    InventoryMismatchError,
    validate_expected_paths,
)


def _inventory(*, media_kind: str = "directory", media_mode: int = 0o750) -> dict[str, object]:
    uid = 1000
    paths = []
    for path, mode in EXPECTED_WEF_PATHS.items():
        if path in {"/home/nuc/wef/media/originals", "/home/nuc/wef/media/public"}:
            paths.append(
                {
                    "path": path,
                    "kind": media_kind,
                    "mode": media_mode if media_kind == "directory" else 0o777,
                    "uid": uid,
                    "gid": uid,
                },
            )
            continue
        paths.append(
            {
                "path": path,
                "kind": "directory",
                "mode": mode,
                "uid": uid,
                "gid": uid,
            },
        )
    return {"uid": uid, "wef_paths": paths}


class ValidateExpectedPathsTests(unittest.TestCase):
    def test_accepts_plain_media_directories(self) -> None:
        validate_expected_paths(_inventory())

    def test_accepts_activated_media_symlinks(self) -> None:
        validate_expected_paths(_inventory(media_kind="symlink", media_mode=0o777))

    def test_rejects_symlink_outside_media_trees(self) -> None:
        payload = _inventory()
        for entry in cast("list[dict[str, object]]", payload["wef_paths"]):
            if entry["path"] == "/home/nuc/wef/media/reports":
                entry["kind"] = "symlink"
                entry["mode"] = 0o777
        with self.assertRaises(InventoryMismatchError):
            validate_expected_paths(payload)


if __name__ == "__main__":
    unittest.main()
