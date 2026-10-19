"""Synthetic host collection and unrelated-workload drift boundaries."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast
from unittest import mock

from scripts.deploy import shared_edge_inventory as inventory
from scripts.test_shared_edge_inventory import sample_inventory


class SharedEdgeInventoryBoundaryTests(unittest.TestCase):
    """Process results are invented; capture never inspects the actual host."""

    def test_tcp_udp_columns_retain_protocol_and_every_watched_listener(self) -> None:
        listeners = (
            "\ntcp LISTEN 0 128 127.0.0.1:3000 0.0.0.0:*\n"
            "udp UNCONN 0 0 [::]:51820 [::]:*\n"
            "tcp LISTEN 0 128 127.0.0.1:9999 0.0.0.0:*\n"
            "tcp LISTEN 0 128 endpoint 0.0.0.0:*\n"
            "tcp LISTEN 0 128 *:service 0.0.0.0:*\n"
            "tcp LISTEN 0 128 127.0.0.1:3000 0.0.0.0:*"
        )

        def run(command: tuple[str, ...], **_options: object) -> subprocess.CompletedProcess[str]:
            output = ""
            if command[:3] == ("docker", "compose", "ls"):
                output = "  "
            elif command[:3] == ("docker", "ps", "--all"):
                output = ""
            elif command[:3] == ("docker", "network", "ls"):
                output = (
                    '\n{"Name":"z-network","ID":"z","Driver":"bridge","Scope":"local"}\n'
                    '\n{"Name":"a-network","ID":"a"}'
                )
            elif command[0] == "/fixture/ss":
                output = listeners
            elif command == ("hostname",):
                output = "fixture-host\n"
            elif command == ("id", "-u"):
                output = "1000\n"
            else:
                message = f"Unexpected synthetic command: {command}"
                raise AssertionError(message)
            return subprocess.CompletedProcess(command, 0, output, "")

        with (
            mock.patch(
                "scripts.deploy.shared_edge_inventory.shutil.which", return_value="/fixture/ss"
            ),
            mock.patch(
                "scripts.deploy.shared_edge_inventory.subprocess.run",
                side_effect=run,
            ),
        ):
            captured = inventory.capture_inventory()
        self.assertEqual(captured["listeners"], ["tcp 127.0.0.1:3000", "udp [::]:51820"])
        self.assertEqual(captured["containers"], [])
        self.assertEqual(captured["compose_projects"], [])
        self.assertEqual(
            [item["name"] for item in captured["networks"]], ["a-network", "z-network"]
        )
        self.assertEqual(captured["hostname"], "fixture-host")

    def test_capture_projects_and_containers_sort_redacted_fields(self) -> None:
        containers = [
            {
                "Id": "b",
                "Name": "/z-container",
                "Image": "image-b",
                "Config": {"Image": "fixture-b", "Env": ["SYNTHETIC_PRIVATE=value"]},
                "State": {"Status": "running", "Health": {"Status": "healthy"}},
                "HostConfig": {"PortBindings": {}},
            },
            {
                "Id": "a",
                "Name": "/a-container",
                "Image": "image-a",
                "Config": {"Image": "fixture-a"},
                "State": {"Status": "exited"},
                "HostConfig": {"PortBindings": {}},
            },
        ]
        results = [
            json.dumps([{"Name": "z-project"}, {"Name": "a-project"}]),
            "b a",
            json.dumps(containers),
            "fixture-host",
            "",
            "",
            "1000",
        ]
        with (
            mock.patch(
                "scripts.deploy.shared_edge_inventory.shutil.which", return_value="/fixture/ss"
            ),
            mock.patch(
                "scripts.deploy.shared_edge_inventory.subprocess.run",
                side_effect=[subprocess.CompletedProcess([], 0, output, "") for output in results],
            ) as run,
        ):
            captured = inventory.capture_inventory()
        self.assertEqual(
            [item["Name"] for item in captured["compose_projects"]], ["a-project", "z-project"]
        )
        self.assertEqual(
            [item["name"] for item in captured["containers"]], ["a-container", "z-container"]
        )
        self.assertIsNone(captured["containers"][0]["health"])
        self.assertNotIn("SYNTHETIC_PRIVATE", json.dumps(captured))
        self.assertTrue(run.call_args_list[2].args[0][:2] == ("docker", "inspect"))

    def test_listener_collection_refuses_missing_tool_and_malformed_output(self) -> None:
        with (
            mock.patch("scripts.deploy.shared_edge_inventory.shutil.which", return_value=None),
            mock.patch(
                "scripts.deploy.shared_edge_inventory.subprocess.run",
                side_effect=[
                    subprocess.CompletedProcess([], 0, output, "")
                    for output in ("[]", "", "fixture-host")
                ],
            ),
            self.assertRaisesRegex(inventory.SharedEdgeInventoryError, "ss is required"),
        ):
            inventory.capture_inventory()
        with (
            mock.patch(
                "scripts.deploy.shared_edge_inventory.shutil.which", return_value="/fixture/ss"
            ),
            mock.patch(
                "scripts.deploy.shared_edge_inventory.subprocess.run",
                side_effect=[
                    subprocess.CompletedProcess([], 0, output, "")
                    for output in ("[]", "", "fixture-host", "tcp too-short")
                ],
            ),
            self.assertRaisesRegex(inventory.SharedEdgeInventoryError, "invalid row"),
        ):
            inventory.capture_inventory()

    def test_identity_projects_forecast_and_other_containers_each_refuse_drift(self) -> None:
        before = cast("dict[str, Any]", sample_inventory())
        for field, value, message in (
            ("hostname", "other-host", "identity changed"),
            ("uid", "2000", "identity changed"),
            ("compose_projects", [], "unrelated Compose project"),
        ):
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(inventory.SharedEdgeInventoryError, message),
            ):
                inventory.compare(before, {**before, field: value})
        changed = copy.deepcopy(before)
        changed["containers"].append({"name": "unrelated-container", "state": "running"})
        with self.assertRaisesRegex(inventory.SharedEdgeInventoryError, "unrelated container"):
            inventory.compare(before, changed)
        changed = copy.deepcopy(before)
        changed["containers"][1]["state"] = "exited"
        with self.assertRaisesRegex(inventory.SharedEdgeInventoryError, "AI Forecast container"):
            inventory.compare(before, changed)

    def test_cli_capture_compare_bad_schema_and_real_entrypoint(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, after = root / "nested/before.json", root / "after.json"
            with (
                mock.patch.object(inventory, "capture_inventory", return_value=sample_inventory()),
                mock.patch("sys.stdout", new_callable=StringIO) as out,
            ):
                self.assertEqual(inventory.main(["capture", str(path)]), 0)
                self.assertIn("Wrote", out.getvalue())
            after.write_text(path.read_text(), encoding="utf-8")
            with mock.patch("sys.stdout", new_callable=StringIO) as out:
                self.assertEqual(inventory.main(["compare", str(path), str(after)]), 0)
                self.assertIn("comparison passed", out.getvalue())
            for raw in ("[]", '{"schema":"wrong"}', "{"):
                after.write_text(raw, encoding="utf-8")
                with self.subTest(raw=raw), mock.patch("sys.stderr", new_callable=StringIO) as err:
                    self.assertEqual(inventory.main(["compare", str(path), str(after)]), 1)
                    self.assertIn("inventory failed", err.getvalue())
            with (
                mock.patch.object(
                    inventory,
                    "capture_inventory",
                    side_effect=subprocess.CalledProcessError(1, ["fixture"]),
                ),
                mock.patch("sys.stderr", new_callable=StringIO),
            ):
                self.assertEqual(inventory.main(["capture", str(after)]), 1)
            after.write_text("[]", encoding="utf-8")
            completed = subprocess.run(  # noqa: S603 - fixed module and synthetic inventory files
                [
                    sys.executable,
                    "-m",
                    "scripts.deploy.shared_edge_inventory",
                    "compare",
                    str(path),
                    str(after),
                ],
                cwd=Path(inventory.__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("invalid schema", completed.stderr)
