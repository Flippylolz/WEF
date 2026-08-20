"""Route-specific smoke checks for shared-edge cutover rehearsals."""

from __future__ import annotations

# ruff: noqa: D102, PLR2004, T201
import json
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pathlib import Path


class SharedEdgeSmokeError(RuntimeError):
    """Raised when a cutover smoke expectation fails."""


class CurlCallable(Protocol):
    """Minimal HTTP client used by smoke checks."""

    def __call__(
        self,
        url: str,
        *,
        resolve: str | None = None,
        cacert: Path | None = None,
        method: str | None = None,
    ) -> tuple[int, dict[str, str], str]: ...


@dataclass(frozen=True, slots=True)
class SmokeTarget:
    """Host-header and listener coordinates for one smoke pass."""

    wef_hostname: str
    http_port: int
    https_port: int
    forecast_hostname: str | None = None
    bind_address: str = "127.0.0.1"


def _resolve(hostname: str, port: int, bind_address: str) -> str:
    return f"{hostname}:{port}:{bind_address}"


def _assert_fixture_body(url: str, body: str, fixture_name: str) -> None:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as error:
        msg = f"HTTPS smoke for {url} returned a non-JSON body"
        raise SharedEdgeSmokeError(msg) from error
    if payload.get("fixture") != fixture_name:
        msg = f"HTTPS smoke for {url} hit unexpected fixture {payload.get('fixture')!r}"
        raise SharedEdgeSmokeError(msg)


def smoke_https_routes(
    curl: CurlCallable,
    target: SmokeTarget,
    *,
    cacert: Path | None = None,
    expect_fixture_bodies: bool = True,
) -> None:
    """Prove WEF web/API/media and optional Forecast HTTPS routes through the edge."""
    wef_resolve = _resolve(target.wef_hostname, target.https_port, target.bind_address)
    checks: list[tuple[str, str, str]] = [
        (f"https://{target.wef_hostname}:{target.https_port}/", wef_resolve, "wef-web"),
        (
            f"https://{target.wef_hostname}:{target.https_port}/api/v1/health/ready",
            wef_resolve,
            "wef-api",
        ),
        (
            f"https://{target.wef_hostname}:{target.https_port}/media/derivatives/x.webp",
            wef_resolve,
            "wef-media",
        ),
    ]
    if target.forecast_hostname is not None:
        forecast_resolve = _resolve(
            target.forecast_hostname,
            target.https_port,
            target.bind_address,
        )
        checks.append(
            (
                f"https://{target.forecast_hostname}:{target.https_port}/",
                forecast_resolve,
                "forecast",
            ),
        )
    for url, resolve, fixture_name in checks:
        status, _headers, body = curl(url, resolve=resolve, cacert=cacert)
        if status != 200:
            msg = f"HTTPS smoke failed for {url}: status={status}"
            raise SharedEdgeSmokeError(msg)
        if expect_fixture_bodies:
            _assert_fixture_body(url, body, fixture_name)


def smoke_http_redirect(
    curl: CurlCallable,
    target: SmokeTarget,
    *,
    hostname: str,
    attempts: int = 10,
    delay_seconds: float = 0.5,
) -> None:
    """Prove non-ACME HTTP traffic redirects to HTTPS for one hostname."""
    resolve = _resolve(hostname, target.http_port, target.bind_address)
    last_status = 0
    last_location = ""
    for _ in range(attempts):
        status, headers, _body = curl(
            f"http://{hostname}:{target.http_port}/",
            resolve=resolve,
        )
        last_status = status
        last_location = headers.get("location", "")
        if status == 301 and last_location.startswith(f"https://{hostname}"):
            return
        time.sleep(delay_seconds)
    if last_status != 301:
        msg = f"HTTP redirect smoke expected 301 for {hostname}, got {last_status}"
        raise SharedEdgeSmokeError(msg)
    msg = f"HTTP redirect Location for {hostname} is unsafe: {last_location!r}"
    raise SharedEdgeSmokeError(msg)


def smoke_http_no_redirect(
    curl: CurlCallable,
    target: SmokeTarget,
) -> None:
    """Prove the pre-redirect TLS stage still answers HTTP with 404."""
    resolve = _resolve(target.wef_hostname, target.http_port, target.bind_address)
    status, headers, _body = curl(
        f"http://{target.wef_hostname}:{target.http_port}/",
        resolve=resolve,
    )
    if status != 404 or "location" in headers:
        msg = "pre-redirect HTTP smoke must answer 404 without Location"
        raise SharedEdgeSmokeError(msg)


def smoke_both_https_and_redirects(
    curl: CurlCallable,
    target: SmokeTarget,
    *,
    cacert: Path | None = None,
    expect_fixture_bodies: bool = True,
) -> None:
    """Run the full post-redirect smoke gate used by the cutover orchestrator."""
    smoke_https_routes(
        curl,
        target,
        cacert=cacert,
        expect_fixture_bodies=expect_fixture_bodies,
    )
    smoke_http_redirect(curl, target, hostname=target.wef_hostname)
    if target.forecast_hostname is not None:
        smoke_http_redirect(curl, target, hostname=target.forecast_hostname)


def build_fixture_smoke_target(
    *,
    http_port: int = 18080,
    https_port: int = 18443,
) -> SmokeTarget:
    """Return the reserved .test fixture smoke coordinates."""
    return SmokeTarget(
        wef_hostname="wef.test",
        forecast_hostname="forecast.test",
        http_port=http_port,
        https_port=https_port,
    )


def main() -> int:
    """Document that live smokes run through the cutover orchestrator/proof."""
    print("shared_edge_smoke: import the smoke helpers from the cutover/proof tools")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
