"""Source-free host collector projections with invented commands and resources."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import json
import runpy
import subprocess
import unittest
import urllib.error
from email.message import Message
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import mock

from scripts.deploy import server_inventory as inventory


class ServerInventoryTests(unittest.TestCase):
    """No Docker daemon, host service or production path is inspected."""

    def test_capture_preserves_schema_sorting_redaction_metadata_and_probe_bounds(self) -> None:
        inspected = [
            {
                "Id": "z",
                "Name": "/z-container",
                "Image": "image-z",
                "Config": {"Image": "fixture-z", "Env": ["SYNTHETIC_PRIVATE=not-exported"]},
                "State": {"Status": "running", "Health": {"Status": "healthy"}},
                "HostConfig": {"PortBindings": {}},
            },
            {
                "Id": "a",
                "Name": "/a-container",
                "Image": "image-a",
                "Config": {"Image": "fixture-a"},
                "State": {"Status": "exited", "Health": None},
                "HostConfig": {"PortBindings": {}},
            },
        ]
        listener_lines = (
            "\ntcp short\n"
            "tcp LISTEN 0 128 127.0.0.1:22 0.0.0.0:*\n"
            "udp UNCONN 0 0 [::]:51820 [::]:*\n"
            "tcp LISTEN 0 128 127.0.0.1:22 0.0.0.0:*\n"
            "tcp LISTEN 0 128 127.0.0.1:9999 0.0.0.0:*\n"
        )
        outputs = {
            ("docker", "compose", "ls", "--all", "--format", "json"): json.dumps(
                [{"Name": "z-project"}, {"Name": "a-project"}]
            ),
            ("docker", "ps", "--all", "--quiet"): "z a",
            ("docker", "inspect", "z", "a"): json.dumps(inspected),
            ("ss", "-H", "-lntu"): listener_lines,
        }

        def run(command: tuple[str, ...], **options: object) -> subprocess.CompletedProcess[str]:
            self.assertEqual(options, {"check": True, "capture_output": True, "text": True})
            return subprocess.CompletedProcess(command, 0, outputs[command], "")

        response = mock.MagicMock()
        response.status = 204
        response.__enter__.return_value = response
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory, file, link, dangling, missing = (
                root / name for name in ("directory", "file", "link", "dangling", "missing")
            )
            directory.mkdir()
            directory.chmod(0o750)
            file.write_text("invented", encoding="utf-8")
            file.chmod(0o640)
            link.symlink_to(directory)
            dangling.symlink_to(missing)
            meminfo = root / "meminfo"
            meminfo.write_text("MemTotal: 100 kB\nMemAvailable: 42 kB\n", encoding="utf-8")
            with (
                mock.patch.object(
                    inventory, "WEF_PATHS", (directory, file, link, dangling, missing)
                ),
                mock.patch.object(inventory, "MEMINFO_PATH", meminfo),
                mock.patch(
                    "scripts.deploy.server_inventory.subprocess.run", side_effect=run
                ) as commands,
                mock.patch(
                    "scripts.deploy.server_inventory.shutil.disk_usage",
                    return_value=SimpleNamespace(free=500),
                ),
                mock.patch(
                    "scripts.deploy.server_inventory.socket.gethostname",
                    return_value="fixture-host",
                ),
                mock.patch("scripts.deploy.server_inventory.os.getuid", return_value=1000),
                mock.patch(
                    "scripts.deploy.server_inventory.urllib.request.urlopen",
                    side_effect=[
                        response,
                        urllib.error.HTTPError(
                            "http://127.0.0.1:8080/", 503, "synthetic", Message(), None
                        ),
                    ],
                ) as urlopen,
                mock.patch("sys.stdout", new_callable=StringIO) as out,
            ):
                self.assertEqual(inventory.main(), 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["schema"], "wef-server-inventory@1")
            self.assertEqual(payload["hostname"], "fixture-host")
            self.assertEqual(payload["uid"], 1000)
            self.assertEqual(
                payload["resources"], {"disk_free_bytes": 500, "memory_available_kb": 42}
            )
            self.assertEqual(payload["existing_http"], {"3000": 204, "8080": 503})
            self.assertEqual(
                [item["Name"] for item in payload["compose_projects"]], ["a-project", "z-project"]
            )
            self.assertEqual(
                [item["name"] for item in payload["containers"]], ["a-container", "z-container"]
            )
            self.assertIsNone(payload["containers"][0]["health"])
            self.assertEqual(
                set(payload["containers"][0]),
                {"id", "name", "image_id", "image_name", "state", "health", "ports"},
            )
            self.assertNotIn("SYNTHETIC_PRIVATE", out.getvalue())
            self.assertEqual(
                payload["listeners"], ["tcp 127.0.0.1:22", "tcp 127.0.0.1:22", "udp [::]:51820"]
            )
            self.assertEqual(
                [item["kind"] for item in payload["wef_paths"]],
                ["directory", "other", "symlink", "symlink"],
            )
            self.assertEqual(payload["wef_paths"][0]["mode"], 0o750)
            self.assertEqual(payload["wef_paths"][1]["mode"], 0o640)
            self.assertEqual(out.getvalue(), json.dumps(payload, sort_keys=True) + "\n")
            self.assertEqual(commands.call_count, 4)
            self.assertEqual(
                urlopen.call_args_list,
                [
                    mock.call("http://127.0.0.1:3000/", timeout=5),
                    mock.call("http://127.0.0.1:8080/", timeout=5),
                ],
            )
            response.read.assert_called_once_with(1)

    def test_empty_docker_and_listener_results_remain_empty(self) -> None:
        with mock.patch(
            "scripts.deploy.server_inventory.subprocess.run",
            side_effect=[subprocess.CompletedProcess([], 0, text, "") for text in (" ", "", "")],
        ):
            self.assertEqual(inventory.compose_projects(), [])
            self.assertEqual(inventory.containers(), [])
            self.assertEqual(inventory.listeners(), [])

    def test_unavailable_http_and_missing_or_invalid_memory_evidence(self) -> None:
        for error in (OSError("synthetic unavailable"), TimeoutError("synthetic timeout")):
            with (
                self.subTest(error=error),
                mock.patch(
                    "scripts.deploy.server_inventory.urllib.request.urlopen", side_effect=error
                ),
            ):
                self.assertIsNone(inventory.http_status(3000))
        with TemporaryDirectory() as temporary:
            meminfo = Path(temporary) / "meminfo"
            for text, error_type in (
                ("MemTotal: 100 kB\n", RuntimeError),
                ("MemAvailable: invalid kB\n", ValueError),
            ):
                meminfo.write_text(text, encoding="utf-8")
                with (
                    self.subTest(text=text),
                    mock.patch.object(inventory, "MEMINFO_PATH", meminfo),
                    self.assertRaises(error_type),
                ):
                    inventory.memory_available_kb()

    def test_script_entrypoint_uses_only_synthetic_host_observers(self) -> None:
        script = str(Path(inventory.__file__).resolve())
        with (
            mock.patch("shutil.disk_usage", return_value=SimpleNamespace(free=500)),
            mock.patch("socket.gethostname", return_value="fixture-host"),
            mock.patch("os.getuid", return_value=1000),
            mock.patch(
                "subprocess.run",
                side_effect=[
                    subprocess.CompletedProcess([], 0, text, "") for text in ("[]", "", "")
                ],
            ),
            mock.patch("urllib.request.urlopen", side_effect=OSError("synthetic unavailable")),
            mock.patch("pathlib.Path.read_text", return_value="MemAvailable: 42 kB\n"),
            mock.patch("pathlib.Path.exists", return_value=False),
            mock.patch("pathlib.Path.is_symlink", return_value=False),
            mock.patch("sys.stdout", new_callable=StringIO) as out,
            self.assertRaises(SystemExit) as result,
        ):
            runpy.run_path(script, run_name="__main__")
        self.assertEqual(result.exception.code, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["schema"], "wef-server-inventory@1")
        self.assertEqual(payload["wef_paths"], [])
        self.assertEqual(payload["existing_http"], {"3000": None, "8080": None})
