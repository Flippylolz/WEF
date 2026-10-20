"""Measure every runtime shell entrypoint with isolated synthetic Docker and HTTP tools."""

# This proof driver is test infrastructure, not production coverage scope.
# ruff: noqa: D101, D102, PT009, T201

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from itertools import count
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from scripts import prove_deploy_rollback as proof

ROOT = Path("/workspace")
DEPLOY = ROOT / "scripts/deploy"
OUTPUT = Path("/coverage")
RAW = OUTPUT / "raw"
CASE_IDS = count(1)
EXCLUDED_SHELL = {"scripts/check_openapi_compatibility.sh"}
SHELL_FILES: list[Path] = []

FAKE_DOCKER = r"""#!/usr/local/bin/python3
import json, os, pathlib, sys
args = sys.argv[1:]
with open(os.environ['WEF_FAKE_DOCKER_LOG'], 'a') as stream:
    stream.write(json.dumps(args) + '\n')
flat = ' '.join(args)
if os.environ.get('FAKE_DOCKER_FAIL') and os.environ['FAKE_DOCKER_FAIL'] in flat:
    raise SystemExit(9)
if args[:2] == ['network', 'inspect']:
    raise SystemExit(0 if os.environ.get('FAKE_NETWORK') == '1' else 1)
if args and args[0] == 'inspect':
    if len(args) > 2:
        print(json.dumps({'wef-edge': {}} if os.environ.get('FAKE_CONNECTED') == '1' else {}))
    elif os.environ.get('FAKE_MISSING', '') == args[-1] or os.environ.get('FAKE_MISSING') == '*':
        raise SystemExit(1)
    else:
        print('[]')
elif args[:2] == ['compose', 'ls']:
    print('[]')
elif args and args[0] == 'ps':
    pass
elif args and args[0] == 'compose':
    if 'ps' in args and os.environ.get('FAKE_EDGE', '1') == '1':
        print('synthetic-edge')
    if 'certbot' in args and os.environ.get('FAKE_RENEW_MARKER') == '1':
        marker = pathlib.Path(os.environ['WEF_SHARED_EDGE_ROOT']) / 'state/reload-requested'
        marker.parent.mkdir(exist_ok=True)
        marker.write_text('synthetic lineage\n')
"""


class ShellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir="/work")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "wef"
        self.bin = self.base / "bin"
        self.bin.mkdir()
        for name in ("state", "postgres", "media", "caddy-data"):
            (self.root / name).mkdir(parents=True)
        proof.write_executable(self.bin / "docker", FAKE_DOCKER)
        proof.write_executable(self.bin / "curl", proof.FAKE_CURL)
        proof.write_executable(self.bin / "sleep", "#!/bin/sh\nexit 0\n")
        proof.write_executable(self.bin / "flock", '#!/bin/sh\nexit "${FAKE_LOCK_STATUS:-0}"\n')
        proof.write_executable(self.bin / "ss", '#!/bin/sh\nprintf "%s" "${FAKE_LISTENER:-}"\n')
        self.memory = self.base / "meminfo"
        self.memory.write_text("MemAvailable: 8388608 kB\n")
        self.environment = {
            "PATH": f"{self.bin}:/usr/local/bin:/usr/bin:/bin",
            "HOME": "/home/nuc",
            "TMPDIR": str(self.base),
            "WEF_FAKE_DOCKER_LOG": str(self.base / "docker.log"),
            "WEF_DEPLOY_TEST_MODE": "1",
            "WEF_MIN_FREE_KB": "1",
            "WEF_MIN_AVAILABLE_MEMORY_KB": "1",
            "WEF_MEMINFO_FILE": str(self.memory),
            "WEF_PUBLIC_HTTPS_BASE_URL": "https://wef.test",
        }
        self.sha = "a" * 40
        self.release, self.config = proof.prepare_release(self.root, self.sha)

    def commands(self) -> list[list[str]]:
        log = Path(self.environment["WEF_FAKE_DOCKER_LOG"])
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def run_shell(
        self,
        script: Path,
        args: Sequence[str | Path] = (),
        *,
        expected: int = 0,
        changes: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        case_id = next(CASE_IDS)
        result = subprocess.run(  # noqa: S603 - fixed collector and synthetic fixture arguments
            [
                "/usr/local/bin/kcov",
                "--bash-method=DEBUG",
                "--bash-dont-parse-binary-dir",
                "--bash-parse-files-in-dir="
                + ",".join(map(str, sorted({p.parent for p in SHELL_FILES}))),
                "--include-pattern=" + ",".join(map(str, SHELL_FILES)),
                str(RAW / f"case-{case_id:04d}"),
                str(script),
                *map(str, args),
            ],
            env={**self.environment, **(changes or {})},
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def common(
        self,
        body: str,
        args: Sequence[str | Path] = (),
        *,
        expected: int = 0,
        changes: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        driver = self.base / "driver.sh"
        proof.write_executable(
            driver,
            f'#!/bin/sh\nset -eu\nSCRIPT_DIR={DEPLOY}\n. "$SCRIPT_DIR/production-common.sh"\n'
            + body
            + "\n",
        )
        return self.run_shell(driver, args, expected=expected, changes=changes)

    def context(self) -> list[str | Path]:
        return [self.root, self.release, self.config, self.sha, "43100"]

    def test_smoke_contracts_and_cleanup(self) -> None:
        for args in ([], ["one"], ["one", "two", "three", "four"]):
            with self.subTest(args=args):
                self.assertIn(
                    "usage:", self.run_shell(DEPLOY / "smoke.sh", args, expected=2).stderr
                )
        for style in ([], ["https://tiles.openfreemap.org/styles/dark"]):
            result = self.run_shell(
                DEPLOY / "smoke.sh",
                ["http://synthetic.test/", self.sha, *style],
                changes={"WEF_RELEASE_SHA": self.sha},
            )
            self.assertIn("production smoke passed", result.stdout)
        before = set(self.base.iterdir())
        self.run_shell(
            DEPLOY / "smoke.sh",
            ["http://synthetic.test", "b" * 40],
            expected=1,
            changes={"WEF_RELEASE_SHA": "b" * 40},
        )
        self.assertEqual(set(self.base.iterdir()), before)

    def test_common_context_refusals(self) -> None:
        self.common('initialize_release_context "$@"', self.context())
        bad: list[list[str | Path]] = [
            [],
            [*self.context()[:3], "a" * 39, "43100"],
            [*self.context()[:3], "G" * 40, "43100"],
            [*self.context()[:4], "bad"],
            [*self.context()[:4], "1"],
            [*self.context()[:4], "65536"],
            [self.root, self.base, *self.context()[2:]],
            [self.root, self.release, self.base / "production.env", self.sha, "43100"],
        ]
        for args in bad:
            self.assertIn(
                "deployment error:",
                self.common('initialize_release_context "$@"', args, expected=1).stderr,
            )
        self.assertIn(
            "production root",
            self.common(
                'initialize_release_context "$@"',
                self.context(),
                expected=1,
                changes={"WEF_DEPLOY_TEST_MODE": "0"},
            ).stderr,
        )
        requirements: tuple[tuple[str, Sequence[str | Path], str], ...] = (
            ('require_command "$1"', ["invented-missing-tool"], "required command"),
            ('require_file "$1"', [self.base / "missing"], "required file"),
            ('require_directory "$1"', [self.base / "missing"], "required directory"),
        )
        for body, helper_args, expected_text in requirements:
            self.assertIn(expected_text, self.common(body, helper_args, expected=1).stderr)

    def test_runtime_directory_permissions_and_refusals(self) -> None:
        self.common("WEF_ROOT=$1\nprepare_runtime_directories", [self.root])
        for relative in ("media", "media/reports", "media/originals", "media/public"):
            self.assertEqual((self.root / relative).stat().st_mode & 0o777, 0o750)
        self.assertEqual((self.root / "secrets/telegram").stat().st_mode & 0o777, 0o700)
        regular = self.base / "regular"
        regular.write_text("synthetic")
        link = self.base / "link"
        link.symlink_to(regular)
        for path, text in ((link, "symlink"), (regular, "must be a directory")):
            self.assertIn(
                text, self.common('require_plain_runtime_directory "$1"', [path], expected=1).stderr
            )
        self.assertIn(
            "must be a directory",
            self.common(
                'require_media_tree_directory "$1" originals', [regular], expected=1
            ).stderr,
        )
        for leaf in ("originals", "public"):
            target = self.root / "candidates" / self.sha / "media" / leaf
            target.mkdir(parents=True)
            path = self.base / f"{leaf}-link"
            path.symlink_to(target)
            self.common(
                'WEF_ROOT=$1\nrequire_media_tree_directory "$2" "$3"', [self.root, path, leaf]
            )
            target.rmdir()
            target.write_text("synthetic")
            self.assertIn(
                "target must be a directory",
                self.common(
                    'WEF_ROOT=$1\nrequire_media_tree_directory "$2" "$3"',
                    [self.root, path, leaf],
                    expected=1,
                ).stderr,
            )
        self.assertIn(
            "under candidates",
            self.common(
                'WEF_ROOT=$1\nrequire_media_tree_directory "$2" originals',
                [self.root, link],
                expected=1,
            ).stderr,
        )

    def test_preflight_resource_and_port_gates(self) -> None:
        self.assertIn(
            "preflight passed", self.run_shell(DEPLOY / "preflight.sh", self.context()).stdout
        )
        for changes, text in (
            ({"WEF_MIN_FREE_KB": "999999999999"}, "free disk space"),
            ({"WEF_MIN_AVAILABLE_MEMORY_KB": "999999999999"}, "available memory"),
            (
                {"FAKE_EDGE": "0", "FAKE_LISTENER": "synthetic occupied socket"},
                "port is already occupied",
            ),
        ):
            self.assertIn(
                text,
                self.run_shell(
                    DEPLOY / "preflight.sh", self.context(), expected=1, changes=changes
                ).stderr,
            )

    def test_reconnect_is_scoped_and_idempotent(self) -> None:
        self.assertIn(
            "absent; skipping", self.run_shell(DEPLOY / "reconnect-wef-upstreams.sh").stdout
        )
        self.environment["FAKE_NETWORK"] = "1"
        result = self.run_shell(DEPLOY / "reconnect-wef-upstreams.sh")
        self.assertIn("signaled", result.stdout)
        connects = [row for row in self.commands() if row[:2] == ["network", "connect"]]
        self.assertEqual(
            connects,
            [
                ["network", "connect", "--alias", alias, "wef-edge", container]
                for alias, container in [
                    ("wef-api", "wef-production-api-1"),
                    ("wef-web", "wef-production-web-1"),
                    ("wef-media", "wef-production-media-edge-1"),
                ]
            ],
        )
        result = self.run_shell(
            DEPLOY / "reconnect-wef-upstreams.sh", changes={"FAKE_CONNECTED": "1"}
        )
        self.assertEqual(result.stdout.count("already on wef-edge"), 3)
        self.assertEqual(
            len([row for row in self.commands() if row[:2] == ["network", "connect"]]), 3
        )
        result = self.run_shell(
            DEPLOY / "reconnect-wef-upstreams.sh", changes={"FAKE_MISSING": "*"}
        )
        self.assertEqual(result.stderr.count("(skip)"), 3)
        self.assertIn("without reload", result.stderr)
        self.run_shell(
            DEPLOY / "reconnect-wef-upstreams.sh",
            expected=9,
            changes={"FAKE_DOCKER_FAIL": "network connect"},
        )

    def test_renewal_validates_before_reload(self) -> None:
        script = DEPLOY / "shared_edge_renew.sh"
        self.assertIn("usage:", self.run_shell(script, expected=2).stderr)
        self.assertIn(
            "not found",
            self.run_shell(script, [self.base, self.base / "missing"], expected=2).stderr,
        )
        edge = self.base / "edge"
        (edge / "state").mkdir(parents=True)
        compose = edge / "compose.yaml"
        compose.write_text("services: {}\n")
        marker = edge / "state/reload-requested"
        marker.write_text("stale")
        result = self.run_shell(script, [edge, compose])
        self.assertIn("no reload marker", result.stderr)
        self.assertFalse(marker.exists())
        for changes, expected, text in (
            ({"FAKE_DOCKER_FAIL": "certbot"}, 9, "renewal failed"),
            ({"FAKE_RENEW_MARKER": "1", "FAKE_DOCKER_FAIL": "nginx -t"}, 1, "nginx -t failed"),
            (
                {"FAKE_RENEW_MARKER": "1", "FAKE_DOCKER_FAIL": "kill -s HUP"},
                1,
                "graceful reload failed",
            ),
            ({"FAKE_RENEW_MARKER": "1"}, 0, "validated reload complete"),
        ):
            result = self.run_shell(
                script, [edge, compose, "--dry-run"], expected=expected, changes=changes
            )
            self.assertIn(text, result.stdout + result.stderr)
        self.assertFalse(marker.exists())
        commands = self.commands()
        final = commands[-3:]
        self.assertIn("certbot", final[0])
        self.assertEqual(final[0][-1], "--dry-run")
        self.assertEqual(
            final[1][-4:], ["nginx", "-t", "-c", "/etc/nginx-edge/current/active.conf"]
        )
        self.assertEqual(final[2][-4:], ["kill", "-s", "HUP", "nginx"])

    def test_server_inventory_wrapper(self) -> None:
        result = self.run_shell(DEPLOY / "server_inventory.sh")
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "wef-server-inventory@1")
        self.assertEqual(report["containers"], [])

    def test_common_compose_and_shared_edge_paths(self) -> None:
        overlay = self.release / "compose.production-shared-edge.yaml"
        overlay.write_text("services: {}\n")
        body = (
            "WEF_RELEASE_DIR=$1\nWEF_CONFIG_FILE=$2\n"
            "production_compose ps\nbring_up_application_services"
        )
        self.common(body, [self.release, self.config])
        commands = self.commands()
        self.assertTrue(
            any(row[-6:] == ["up", "--detach", "--wait", "api", "web", "edge"] for row in commands)
        )
        self.environment.update(FAKE_NETWORK="1", WEF_DEPLOY_TEST_MODE="0")
        self.common(body, [self.release, self.config])
        self.assertTrue(
            any(str(overlay) in row and row[-1] == "media-edge" for row in self.commands())
        )
        packaged = self.release / "scripts/deploy/reconnect-wef-upstreams.sh"
        packaged.parent.mkdir(parents=True)
        proof.write_executable(packaged, '#!/bin/sh\nprintf "packaged reconnect\\n"\n')
        self.assertIn(
            "packaged reconnect",
            self.common(
                "WEF_RELEASE_DIR=$1\nreconnect_shared_edge_upstreams", [self.release]
            ).stdout,
        )
        packaged.unlink()
        fallback = Path("/home/nuc/wef-shared-edge/ops/reconnect-wef-upstreams.sh")
        fallback.parent.mkdir(parents=True, exist_ok=True)
        proof.write_executable(fallback, '#!/bin/sh\nprintf "legacy reconnect\\n"\n')
        body = 'WEF_RELEASE_DIR=$1\nSCRIPT_DIR=""\nreconnect_shared_edge_upstreams'
        self.assertIn("legacy reconnect", self.common(body, [self.release]).stdout)
        fallback.unlink()
        self.assertIn(
            "reconnect-wef-upstreams.sh is missing",
            self.common(body, [self.release], expected=1).stderr,
        )

    def test_public_https_retry_and_cleanup(self) -> None:
        body = "WEF_RELEASE_SHA=$1\nexport WEF_RELEASE_SHA\nsmoke_public_https_origin"
        self.common(body, [self.sha])
        self.environment["FAKE_NETWORK"] = "1"
        self.assertIn("Public HTTPS smoke passed", self.common(body, [self.sha]).stdout)
        proof.write_executable(
            self.bin / "curl", '#!/bin/sh\nprintf "attempt\\n" >> "$WEF_TEST_CURL_LOG"\nexit 22\n'
        )
        log = self.base / "curl.log"
        result = self.common(body, [self.sha], expected=1, changes={"WEF_TEST_CURL_LOG": str(log)})
        self.assertNotIn("Public HTTPS smoke passed", result.stdout)
        self.assertIn("remained unhealthy", result.stderr)
        self.assertEqual(len(log.read_text().splitlines()), 12)
        self.assertFalse(any(path.name.startswith("tmp.") for path in self.base.iterdir()))

    def test_provisioning_boundary_permissions(self) -> None:
        script = DEPLOY / "provision_server.sh"
        proof.write_executable(self.bin / "id", '#!/bin/sh\nprintf "%s\\n" "${FAKE_USER:-nuc}"\n')
        for changes, text in (
            ({"FAKE_USER": "other"}, "expected the nuc account"),
            ({"HOME": "/different"}, "unexpected home directory"),
            ({"FAKE_LISTENER": "synthetic occupied port"}, "port 3100 is already occupied"),
        ):
            self.assertIn(text, self.run_shell(script, expected=1, changes=changes).stderr)
        root = Path("/home/nuc/wef")
        root.symlink_to(self.root)
        self.assertIn("must not be a symlink", self.run_shell(script, expected=1).stderr)
        root.unlink()
        # A synthetic PATH provides all tools except the required socket observer.
        isolated = self.base / "isolated"
        isolated.mkdir()
        for command in ("id", "docker"):
            (isolated / command).symlink_to(self.bin / command)
        for command in ("bash", "python3", "curl", "flock", "awk", "df"):
            tool = (
                self.bin / command
                if (self.bin / command).exists()
                else Path(shutil.which(command) or "/missing-fixture-tool")
            )
            (isolated / command).symlink_to(tool)
        self.assertIn(
            "required command is unavailable: ss",
            self.run_shell(
                script, expected=1, changes={"PATH": f"{isolated}:/usr/local/bin"}
            ).stderr,
        )
        self.assertIn("Prepared the isolated WEF server boundary", self.run_shell(script).stdout)
        for path in (
            "",
            "releases",
            "media",
            "media/originals",
            "media/public",
            "media/reports",
            "imports",
            "imports/incoming",
            "imports/extracted",
            "caddy-data",
            "state",
            "logs",
        ):
            self.assertEqual((root / path).stat().st_mode & 0o777, 0o750)
        for path in ("secrets", "secrets/releases", "secrets/telegram", "postgres"):
            self.assertEqual((root / path).stat().st_mode & 0o777, 0o700)
        self.assertEqual(
            [row[:2] for row in self.commands() if row[:1] == ["compose"]],
            [["compose", "version"], ["compose", "version"]],
        )
        shutil.rmtree(root)

    def test_certbot_hook_permissions_and_atomic_marker(self) -> None:
        script = ROOT / "infra/nginx/deploy-hook.sh"
        tree = Path("/etc/letsencrypt")
        live, archive = tree / "live/synthetic.test", tree / "archive/synthetic.test"
        live.mkdir(parents=True)
        archive.mkdir(parents=True)
        for name in ("cert1.pem", "chain1.pem", "fullchain1.pem", "privkey1.pem"):
            (archive / name).write_text("invented fixture text; no key or certificate\n")
        accounts = tree / "accounts"
        accounts.mkdir()
        accounts.chmod(0o700)
        state = self.base / "edge-state"
        self.environment["WEF_EDGE_STATE_DIR"] = str(state)
        self.assertIn("RENEWED_LINEAGE is not set", self.run_shell(script, expected=1).stderr)
        self.assertIn(
            "does not exist",
            self.run_shell(
                script, expected=1, changes={"RENEWED_LINEAGE": str(self.base / "missing")}
            ).stderr,
        )
        self.environment["RENEWED_LINEAGE"] = str(live)
        self.assertIn("fullchain.pem is not readable", self.run_shell(script, expected=1).stderr)
        (live / "fullchain.pem").write_text("synthetic")
        self.assertIn("privkey.pem is not readable", self.run_shell(script, expected=1).stderr)
        (live / "privkey.pem").write_text("synthetic")
        self.assertIn(
            "fullchain.pem is not a Certbot-managed symlink",
            self.run_shell(script, expected=1).stderr,
        )
        (live / "fullchain.pem").unlink()
        (live / "fullchain.pem").symlink_to("../../archive/synthetic.test/fullchain1.pem")
        self.assertIn(
            "privkey.pem is not a Certbot-managed symlink",
            self.run_shell(script, expected=1).stderr,
        )
        (live / "privkey.pem").unlink()
        (live / "privkey.pem").symlink_to("../../archive/synthetic.test/privkey1.pem")
        self.assertFalse(state.exists())
        result = self.run_shell(script)
        self.assertIn("reload requested", result.stdout)
        self.assertEqual(tree.stat().st_mode & 0o777, 0o711)
        for directory in (live, archive, live.parent, archive.parent):
            self.assertEqual(directory.stat().st_mode & 0o777, 0o755)
        for name in ("cert1.pem", "chain1.pem", "fullchain1.pem"):
            self.assertEqual((archive / name).stat().st_mode & 0o777, 0o644)
        self.assertEqual((archive / "privkey1.pem").stat().st_mode & 0o777, 0o640)
        self.assertEqual((archive / "privkey1.pem").stat().st_gid, 1000)
        self.assertEqual(accounts.stat().st_mode & 0o777, 0o700)
        marker = state / "reload-requested"
        self.assertEqual(marker.read_text(), str(live) + "\n")
        self.assertEqual(marker.stat().st_mode & 0o777, 0o600)
        self.assertFalse((state / ".reload-requested.tmp").exists())
        dry_run = self.base / "dry-run"
        dry_run.mkdir()
        for name in ("fullchain.pem", "privkey.pem"):
            (dry_run / name).write_text("synthetic")
        self.run_shell(script, changes={"RENEWED_LINEAGE": str(dry_run)})
        self.assertEqual(marker.read_text(), str(dry_run) + "\n")

    def test_deployment_activation_and_restoration(self) -> None:
        self.environment.update(
            WEF_RELEASE_OBSERVATION=str(self.root / "state/observation.json"),
            WEF_EXPECTED_CURRENT_SHA="none",
            WEF_SEED_REHEARSAL="1",
        )
        result = self.run_shell(DEPLOY / "deploy.sh", self.context())
        self.assertIn("Activated WEF release", result.stdout)
        self.assertEqual(
            json.loads((self.root / "state/current.json").read_text())["release_sha"], self.sha
        )
        self.assertEqual((self.root / "releases/current").resolve(), self.release.resolve())
        self.assertFalse((self.root / "state/activation-pending.json").exists())
        self.run_shell(DEPLOY / "verify_current.sh", self.context())
        self.environment["WEF_EXPECTED_CURRENT_SHA"] = self.sha
        for candidate, changes, status, text in (
            ("b" * 40, {}, 1, "Previous WEF application release restored"),
            (
                "c" * 40,
                {"WEF_FORCE_ROLLBACK_REHEARSAL": "1", "WEF_DEPLOY_SKIP_PULL": "1"},
                42,
                "Previous WEF application release restored",
            ),
            (
                "d" * 40,
                {"FAKE_DOCKER_FAIL": " migrate"},
                1,
                "existing application release was not replaced",
            ),
        ):
            release, config = proof.prepare_release(self.root, candidate)
            result = self.run_shell(
                DEPLOY / "deploy.sh",
                [self.root, release, config, candidate, "43100"],
                expected=status,
                changes=changes,
            )
            self.assertIn(text, result.stderr)
            self.assertEqual(
                json.loads((self.root / "state/current.json").read_text())["release_sha"], self.sha
            )
        self.run_shell(DEPLOY / "rollback.sh", [self.root, self.root / "state/previous.json"])
        self.assertEqual(
            json.loads((self.root / "state/current.json").read_text())["release_sha"], self.sha
        )
        self.assertIn("usage:", self.run_shell(DEPLOY / "rollback.sh", expected=2).stderr)
        self.assertIn(
            "state must stay under",
            self.run_shell(
                DEPLOY / "rollback.sh", [self.root, self.base / "state.json"], expected=1
            ).stderr,
        )

    def test_deployment_failures_preserve_safety(self) -> None:
        self.assertIn(
            "holds the host lock",
            self.run_shell(
                DEPLOY / "deploy.sh", self.context(), expected=1, changes={"FAKE_LOCK_STATUS": "1"}
            ).stderr,
        )
        result = self.run_shell(
            DEPLOY / "deploy.sh",
            self.context(),
            changes={"WEF_RELEASE_OBSERVATION": str(self.base)},
        )
        self.assertIn("Release observation unavailable.", result.stderr)
        self.assertIn("Activated", result.stdout)
        candidate = "b" * 40
        release, config = proof.prepare_release(self.root, candidate)
        result = self.run_shell(
            DEPLOY / "deploy.sh",
            [self.root, release, config, candidate, "43100"],
            expected=1,
            changes={"FAKE_DOCKER_FAIL": " " + str(self.config) + " "},
        )
        self.assertIn("automatic application rollback failed", result.stderr)
        failure = json.loads((self.root / "state/last-failure.json").read_text())
        self.assertEqual(failure["candidate_release_sha"], candidate)
        (self.root / "state/current.json").unlink()
        result = self.run_shell(
            DEPLOY / "deploy.sh", [self.root, release, config, candidate, "43100"], expected=1
        )
        self.assertIn("No previous release exists", result.stderr)
        self.assertTrue(any(row[-4:] == ["stop", "edge", "web", "api"] for row in self.commands()))

    def test_production_preflight_provider_and_pull_guards(self) -> None:
        root = Path("/home/nuc/wef")
        for name in ("state", "postgres", "media", "caddy-data"):
            (root / name).mkdir(parents=True)
        self.addCleanup(shutil.rmtree, root)
        release, config = proof.prepare_release(root, self.sha)
        text = config.read_text().replace("WEF_BIND_ADDRESS=127.0.0.1", "WEF_BIND_ADDRESS=0.0.0.0")
        text = text.replace("wef-backend:local", "ghcr.io/example/wef-backend@sha256:" + "a" * 64)
        text = text.replace("wef-web:local", "ghcr.io/example/wef-web@sha256:" + "b" * 64)
        config.write_text(text)
        self.environment["WEF_DEPLOY_TEST_MODE"] = "0"
        args: list[str | Path] = [root, release, config, self.sha, "43100"]
        self.assertIn("preflight passed", self.run_shell(DEPLOY / "preflight.sh", args).stdout)
        self.assertIn(
            "pull can be skipped only",
            self.run_shell(
                DEPLOY / "deploy.sh", args, expected=1, changes={"WEF_DEPLOY_SKIP_PULL": "1"}
            ).stderr,
        )
        result = self.run_shell(
            DEPLOY / "deploy.sh", args, expected=1, changes={"FAKE_DOCKER_FAIL": "geocoder-check"}
        )
        self.assertIn("Geoapify readiness failed", result.stderr)
        self.assertFalse((root / "state/current.json").exists())
        self.assertFalse(any("migrate" in row for row in self.commands()))
        result = self.run_shell(DEPLOY / "deploy.sh", args)
        self.assertIn("Activated", result.stdout)
        self.assertIn(
            "holds the host lock",
            self.run_shell(
                DEPLOY / "verify_current.sh", args, expected=1, changes={"FAKE_LOCK_STATUS": "1"}
            ).stderr,
        )
        self.run_shell(DEPLOY / "verify_current.sh", args)
        commands = self.commands()
        pull = max(i for i, row in enumerate(commands) if "pull" in row)
        provider = max(i for i, row in enumerate(commands) if "geocoder-check" in row)
        migrate = max(i for i, row in enumerate(commands) if "migrate" in row)
        self.assertLess(pull, provider)
        self.assertLess(provider, migrate)

    def test_failed_application_or_worker_start_cannot_activate_the_candidate(self) -> None:
        for candidate, failing_command in (
            ("c" * 40, "up --detach --wait api web edge"),
            ("d" * 40, "up --detach telegram-worker"),
        ):
            with self.subTest(command=failing_command):
                self.run_shell(DEPLOY / "deploy.sh", self.context())
                release, config = proof.prepare_release(self.root, candidate)
                failure = f"{config} --file {release / 'compose.production.yaml'} {failing_command}"
                result = self.run_shell(
                    DEPLOY / "deploy.sh",
                    [self.root, release, config, candidate, "43100"],
                    expected=1,
                    changes={"FAKE_DOCKER_FAIL": failure},
                )
                self.assertIn("Previous WEF application release restored", result.stderr)
                state = json.loads((self.root / "state/current.json").read_text())
                self.assertEqual(state["release_sha"], self.sha)
                failure_state = json.loads((self.root / "state/last-failure.json").read_text())
                self.assertEqual(failure_state["candidate_release_sha"], candidate)
                self.assertEqual(failure_state["restored_release_sha"], self.sha)

    def test_shared_edge_application_start_failure_returns_to_its_caller(self) -> None:
        overlay = self.release / "compose.production-shared-edge.yaml"
        overlay.write_text("services: {}\n")
        body = (
            "WEF_RELEASE_DIR=$1\nWEF_CONFIG_FILE=$2\n"
            "if bring_up_application_services; then exit 0; "
            'else status=$?; printf "caller refused start\\n"; exit "$status"; fi'
        )
        result = self.common(
            body,
            [self.release, self.config],
            expected=9,
            changes={
                "WEF_DEPLOY_TEST_MODE": "0",
                "FAKE_NETWORK": "1",
                "FAKE_DOCKER_FAIL": "up --detach --wait api web edge media-edge",
            },
        )
        self.assertIn("caller refused start", result.stdout)
        self.assertFalse(any("telegram-worker" in row for row in self.commands()))

    def test_certificate_traversal_failure_preserves_reload_marker(self) -> None:
        lineage = self.base / "lineage"
        lineage.mkdir()
        for name in ("fullchain.pem", "privkey.pem"):
            (lineage / name).write_text("synthetic text")
        proof.write_executable(self.bin / "find", "#!/bin/sh\nexit 9\n")
        state = self.base / "state"
        state.mkdir()
        marker = state / "reload-requested"
        marker.write_text("prior marker")
        result = self.run_shell(
            ROOT / "infra/nginx/deploy-hook.sh",
            expected=1,
            changes={"RENEWED_LINEAGE": str(lineage), "WEF_EDGE_STATE_DIR": str(state)},
        )
        self.assertIn("cannot open certificate directory traversal", result.stderr)
        self.assertEqual(marker.read_text(), "prior marker")


def run_inside() -> int:
    """Run only inside the disposable container prepared by the host proof."""
    if (
        os.environ.get("WEF_RUNTIME_SHELL_FIXTURE") != "1"
        or not Path("/.dockerenv").is_file()
        or (ROOT / ".shell-coverage-fixture").read_text() != "synthetic source only\n"
    ):
        message = "shell fixture mode requires the isolated, no-network proof container"
        raise RuntimeError(message)
    policy = json.loads((ROOT / ".github/critical-coverage.json").read_text())
    SHELL_FILES.extend(ROOT / name for name in sorted(policy["shell"]))
    RAW.mkdir(parents=True)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ShellTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    subprocess.run(  # noqa: S603 - fixed collector and proof-owned output paths
        [
            "/usr/local/bin/kcov",
            "--merge",
            str(OUTPUT / "merged"),
            *map(str, sorted(RAW.iterdir())),
        ],
        check=True,
        timeout=120,
    )
    shutil.copy2(OUTPUT / "merged/kcov-merged/coverage.json", OUTPUT / "coverage.json")
    report = json.loads((OUTPUT / "coverage.json").read_text())
    for row in sorted(report["files"], key=lambda row: row["file"]):
        print(
            f"{row['file'].removeprefix('/workspace/')}: "
            f"{row['covered_lines']}/{row['total_lines']} lines"
        )
    return int(not result.wasSuccessful())


def run_host() -> int:
    """Mount an explicit source allowlist, never the checkout, credentials or Docker socket."""
    repository = Path(__file__).resolve().parents[1]
    docker, git = shutil.which("docker"), shutil.which("git")
    if docker is None or git is None:
        message = "shell coverage requires Docker and Git on the host"
        raise RuntimeError(message)
    policy = json.loads((repository / ".github/critical-coverage.json").read_text())
    inventory = subprocess.run(  # noqa: S603 - trusted Git executable and fixed read-only inventory
        [git, "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "*.sh"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    if set(inventory.stdout.rstrip("\0").split("\0")) - EXCLUDED_SHELL != set(policy["shell"]):
        message = "runtime shell inventory differs from the reviewed coverage policy"
        raise ValueError(message)
    paths = (
        set(policy["shell"])
        | set(policy["operations"])
        | {
            ".github/critical-coverage.json",
            "scripts/__init__.py",
            "scripts/deploy/__init__.py",
            "scripts/prove_deploy_rollback.py",
            "scripts/prove_runtime_shell.py",
            "infra/compose.production.yaml",
            "infra/Caddyfile.production",
        }
    )
    output = repository / "tmp/coverage/shell"
    if output.is_symlink() or not output.resolve().is_relative_to(repository):
        message = "shell coverage output must stay inside the ignored repository report directory"
        raise ValueError(message)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    uid, gid = os.getuid(), os.getgid()
    with tempfile.TemporaryDirectory(prefix="wef-shell-source-") as temporary:
        fixture = Path(temporary)
        for name in sorted(paths):
            source = repository / name
            if (
                Path(name).is_absolute()
                or ".." in Path(name).parts
                or source.is_symlink()
                or not source.is_file()
                or not source.resolve().is_relative_to(repository)
            ):
                message = f"shell proof source must be a plain repository file: {name}"
                raise ValueError(message)
            destination = fixture / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        (fixture / ".shell-coverage-fixture").write_text("synthetic source only\n")
        image = "wef-shell-coverage:local"
        subprocess.run(  # noqa: S603 - fixed Docker build and tiny tooling-only context
            [docker, "build", "--tag", image, str(repository / "infra/shell-coverage")],
            check=True,
            timeout=600,
        )
        command = [
            docker,
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            f"{uid}:{gid}",
            "--group-add",
            "1000",
            "--tmpfs",
            "/tmp:rw,exec,nosuid,nodev,size=128m,mode=1777",  # noqa: S108 - container tmpfs options
        ]
        for path, size in (("/work", "128m"), ("/home/nuc", "32m"), ("/etc/letsencrypt", "32m")):
            command.extend(
                [
                    "--tmpfs",
                    f"{path}:rw,exec,nosuid,nodev,size={size},uid={uid},gid={gid},mode=0700",
                ]
            )
        command.extend(
            [
                "--volume",
                f"{fixture}:/workspace:ro",
                "--volume",
                f"{output}:/coverage",
                "--workdir",
                "/workspace",
                "--env",
                "WEF_RUNTIME_SHELL_FIXTURE=1",
                "--entrypoint",
                "python3",
                image,
                "-m",
                "scripts.prove_runtime_shell",
                "--inside",
            ]
        )
        subprocess.run(command, check=True, timeout=300)  # noqa: S603 - allowlisted fixture mounts only
    return 0


def main() -> int:
    """Build the pinned test image, run behavioral assertions and retain real Kcov evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inside", action="store_true")
    return run_inside() if parser.parse_args().inside else run_host()


if __name__ == "__main__":
    raise SystemExit(main())
