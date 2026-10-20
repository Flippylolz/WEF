"""Public HTTPS health semantics must gate conditional deployment success."""

# ruff: noqa: D102, PT009

from __future__ import annotations

import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

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
