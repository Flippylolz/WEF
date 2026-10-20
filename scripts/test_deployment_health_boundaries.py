"""Public HTTPS health semantics must gate conditional deployment success."""

# ruff: noqa: D102, PT009

from __future__ import annotations

import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import prove_deploy_rollback as proof
from scripts.deploy.release_state import read_failure_state, read_state

DRIVER = r"""
. "$1"
SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$1")" && pwd)
shared_edge_network_present() { return 0; }
sleep() { :; }
mktemp() {
    mkdir -p "$WEF_TEST_HTTP_TMP"
    printf '%s\n' "$WEF_TEST_HTTP_TMP"
}
curl() {
    fixture_output=''
    fixture_url=''
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --output) shift; fixture_output=$1 ;;
            *) fixture_url=$1 ;;
        esac
        shift
    done
    printf 'request\n' >> "$WEF_TEST_CURL_LOG"
    case "$fixture_url" in
        */api/v1/health/live)
            printf '{"status":"%s"}\n' "$WEF_TEST_LIVE_STATUS" > "$fixture_output"
            ;;
        *) printf '%s\n' "$WEF_TEST_ROOT_BODY" > "$fixture_output" ;;
    esac
}
if smoke_public_https_origin; then
    exit 0
else
    printf 'fixture caller refused health\n'
    exit 1
fi
"""


class DeploymentHealthBoundaryTests(unittest.TestCase):
    """Shell clients are functions that only write invented temporary responses."""

    def test_semantic_failures_cannot_report_conditional_deployment_success(self) -> None:
        shell = shutil.which("sh")
        self.assertIsNotNone(shell)
        script = Path(__file__).parent / "deploy/production-common.sh"
        healthy_body = "<h1>Apartments and houses for sale in Warsaw</h1>"
        for status, body, expected in (
            ("live", healthy_body, 0),
            ("broken", healthy_body, 1),
            ("live", "synthetic unhealthy root", 1),
        ):
            with self.subTest(status=status, body=body), TemporaryDirectory() as temporary:
                root = Path(temporary)
                request_log = root / "requests.log"
                environment = {
                    "PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin",
                    "TMPDIR": str(root),
                    "WEF_PUBLIC_HTTPS_BASE_URL": "https://wef.test/",
                    "WEF_TEST_HTTP_TMP": str(root / "http"),
                    "WEF_TEST_CURL_LOG": str(request_log),
                    "WEF_TEST_LIVE_STATUS": status,
                    "WEF_TEST_ROOT_BODY": body,
                }
                result = subprocess.run(  # noqa: S603 - fixed shell driver and synthetic responses
                    [shell or "/bin/sh", "-c", DRIVER, "fixture", str(script)],
                    env=environment,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertFalse((root / "http").exists())
                self.assertEqual(
                    len(request_log.read_text().splitlines()), 2 if expected == 0 else 24
                )
                if expected:
                    self.assertNotIn("Public HTTPS smoke passed", result.stdout)
                    self.assertIn("remained unhealthy", result.stderr)
                    self.assertIn("fixture caller refused health", result.stdout)

    def test_public_semantic_failure_reaches_the_existing_automatic_rollback(self) -> None:
        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            root, fake_bin = base / "wef", base / "bin"
            for name in ("state", "postgres", "media", "caddy-data"):
                (root / name).mkdir(parents=True)
            fake_bin.mkdir()
            docker = proof.FAKE_DOCKER.replace(
                "#!/bin/sh\n",
                '#!/bin/sh\nif [ "$1" = network ] && [ "$2" = inspect ]; then exit 0; fi\n',
                1,
            )
            proof.write_executable(fake_bin / "docker", docker)
            proof.write_executable(fake_bin / "curl-base", proof.FAKE_CURL)
            proof.write_executable(
                fake_bin / "curl",
                r"""#!/bin/sh
fixture_parse() {
    fixture_output=''
    fixture_url=''
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --output) shift; fixture_output=$1 ;;
            *) fixture_url=$1 ;;
        esac
        shift
    done
}
fixture_parse "$@"
if [ "$WEF_RELEASE_SHA" = "$WEF_TEST_FAILED_SHA" ] &&
   [ "$fixture_url" = https://wef.test/api/v1/health/live ]; then
    printf '{"status":"broken"}\n' > "$fixture_output"
    exit 0
fi
exec "$WEF_TEST_BASE_CURL" "$@"
""",
            )
            for name in ("flock", "ss", "sleep"):
                proof.write_executable(fake_bin / name, "#!/bin/sh\nexit 0\n")
            meminfo = base / "meminfo"
            meminfo.write_text("MemAvailable: 8388608 kB\n", encoding="utf-8")
            healthy, candidate = "a" * 40, "c" * 40
            healthy_dir, healthy_config = proof.prepare_release(root, healthy)
            candidate_dir, candidate_config = proof.prepare_release(root, candidate)
            for directory in (healthy_dir, candidate_dir):
                reconnect = directory / "scripts/deploy/reconnect-wef-upstreams.sh"
                reconnect.parent.mkdir(parents=True)
                proof.write_executable(reconnect, "#!/bin/sh\nexit 0\n")
            environment = {
                "PATH": f"{fake_bin}:{Path(sys.executable).parent}:/usr/bin:/bin",
                "WEF_DEPLOY_SKIP_PULL": "1",
                "WEF_DEPLOY_TEST_MODE": "1",
                "WEF_FAKE_DOCKER_LOG": str(base / "docker.log"),
                "WEF_MEMINFO_FILE": str(meminfo),
                "WEF_MIN_AVAILABLE_MEMORY_KB": "1",
                "WEF_MIN_FREE_KB": "1",
                "WEF_PUBLIC_HTTPS_BASE_URL": "https://wef.test",
                "WEF_TEST_FAILED_SHA": candidate,
                "WEF_TEST_BASE_CURL": str(fake_bin / "curl-base"),
            }
            proof.run_deploy(root, healthy_dir, healthy_config, healthy, environment, check=True)
            failed = proof.run_deploy(
                root, candidate_dir, candidate_config, candidate, environment, check=False
            )
            self.assertEqual(failed.returncode, 1, failed.stderr)
            self.assertIn("Previous WEF application release restored", failed.stderr)
            self.assertEqual(read_state(root / "state/current.json")["release_sha"], healthy)
            failure = read_failure_state(root / "state/last-failure.json")
            self.assertEqual(failure["candidate_release_sha"], candidate)
            self.assertEqual(failure["restored_release_sha"], healthy)
            commands = (base / "docker.log").read_text().splitlines()
            last_candidate = max(
                index for index, command in enumerate(commands) if str(candidate_config) in command
            )
            self.assertTrue(
                any(str(healthy_config) in command for command in commands[last_candidate + 1 :])
            )
