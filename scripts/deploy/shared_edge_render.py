"""Deterministically render and validate shared-edge Nginx/Certbot releases."""

# ruff: noqa: PLR2004, T201
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = REPOSITORY_ROOT / "infra" / "nginx"
BOOTSTRAP_TEMPLATE = "bootstrap.conf.in"
TLS_TEMPLATE = "tls.conf.in"
TLS_REDIRECT_TEMPLATE = "tls-redirect.conf.in"
FORECAST_VHOST_TEMPLATE = "forecast-vhost.conf.in"
HOOK_FILENAME = "deploy-hook.sh"
ISSUANCE_FILENAME = "certbot-issuance.txt"
BOOTSTRAP_CONFIG = "bootstrap.conf"
TLS_CONFIG = "tls.conf"
TLS_REDIRECT_CONFIG = "tls-redirect.conf"
FIXTURE_TLD = ".test"
FIXTURE_ACME_SERVER = "https://pebble:14000/dir"
PRODUCTION_ACME_SERVER = "https://acme-v02.api.letsencrypt.org/directory"
HOSTNAME_PATTERN = re.compile(
    r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?"
    r"(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$"
)
UPSTREAM_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]*:[0-9]{1,5}$")
BODY_SIZE_PATTERN = re.compile(r"^\d{1,4}[kKmMgG]?$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PLACEHOLDER_PATTERN = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
RELEASE_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
FORBIDDEN_PATH_FRAGMENTS = ("..",)


class SharedEdgeRenderError(ValueError):
    """Raised for unsafe, incomplete, or non-deterministic edge rendering."""


@dataclass(frozen=True, slots=True)
class EdgeConfiguration:
    """Validated, non-secret inputs for one shared-edge release."""

    wef_hostname: str
    wef_api_upstream: str
    wef_media_upstream: str
    wef_web_upstream: str
    forecast_hostname: str | None = None
    forecast_upstream: str | None = None
    client_max_body_size: str = "1m"
    acme_server: str | None = None
    email: str | None = None
    fixture_mode: bool = False

    @property
    def resolved_acme_server(self) -> str:
        """Fixture mode can only target the local proof ACME server."""
        if self.acme_server is not None:
            return self.acme_server
        return FIXTURE_ACME_SERVER if self.fixture_mode else PRODUCTION_ACME_SERVER

    @property
    def includes_forecast(self) -> bool:
        """Report whether this release terminates Forecast TLS."""
        return self.forecast_hostname is not None


def validate_hostname(name: str, *, fixture_mode: bool, label: str) -> None:
    """Accept only lowercase DNS hostnames; fixtures must use reserved .test."""
    if not HOSTNAME_PATTERN.fullmatch(name):
        msg = f"{label} is not a valid lowercase DNS hostname: {name!r}"
        raise SharedEdgeRenderError(msg)
    if fixture_mode and not name.endswith(FIXTURE_TLD):
        msg = f"{label} must use the reserved {FIXTURE_TLD} TLD in fixture mode: {name!r}"
        raise SharedEdgeRenderError(msg)


def validate_upstream(value: str, label: str) -> None:
    """Accept only host:port upstream references for proxy_pass rendering."""
    if not UPSTREAM_PATTERN.fullmatch(value):
        msg = f"{label} must be a host:port upstream reference: {value!r}"
        raise SharedEdgeRenderError(msg)


def validate_forecast_pair(config: EdgeConfiguration) -> None:
    """Require Forecast hostname and upstream together, or omit both."""
    if config.forecast_hostname is None:
        if config.forecast_upstream is not None:
            msg = "forecast hostname and upstream must both be set or both omitted"
            raise SharedEdgeRenderError(msg)
        return
    if config.forecast_upstream is None:
        msg = "forecast hostname and upstream must both be set or both omitted"
        raise SharedEdgeRenderError(msg)
    validate_hostname(
        config.forecast_hostname,
        fixture_mode=config.fixture_mode,
        label="AI Forecast hostname",
    )
    if config.wef_hostname == config.forecast_hostname:
        msg = "WEF and AI Forecast hostnames must be distinct"
        raise SharedEdgeRenderError(msg)
    validate_upstream(config.forecast_upstream, "AI Forecast upstream")


def validate_acme_account_policy(config: EdgeConfiguration) -> None:
    """Reject ACME email/server combinations that break fixture/production boundaries."""
    if config.email is not None and not EMAIL_PATTERN.fullmatch(config.email):
        msg = "ACME account email is not a valid address"
        raise SharedEdgeRenderError(msg)
    if config.fixture_mode and config.email is not None:
        msg = "fixture mode must not record a real ACME account email"
        raise SharedEdgeRenderError(msg)
    if config.fixture_mode and config.resolved_acme_server != FIXTURE_ACME_SERVER:
        msg = "fixture mode must target only the local proof ACME server"
        raise SharedEdgeRenderError(msg)
    if not config.fixture_mode and config.acme_server == FIXTURE_ACME_SERVER:
        msg = "production releases must not target the local proof ACME server"
        raise SharedEdgeRenderError(msg)


def validate_configuration(config: EdgeConfiguration) -> None:
    """Reject every input that cannot render a safe deterministic release."""
    validate_hostname(
        config.wef_hostname,
        fixture_mode=config.fixture_mode,
        label="WEF hostname",
    )
    validate_forecast_pair(config)
    for label, value in (
        ("WEF API upstream", config.wef_api_upstream),
        ("WEF media upstream", config.wef_media_upstream),
        ("WEF web upstream", config.wef_web_upstream),
    ):
        validate_upstream(value, label)
    if not BODY_SIZE_PATTERN.fullmatch(config.client_max_body_size):
        msg = "client max body size must be like 1m or 512k"
        raise SharedEdgeRenderError(msg)
    validate_acme_account_policy(config)


def render_template(template: str, replacements: Mapping[str, str]) -> str:
    """Substitute placeholders exactly once and refuse leftover placeholders."""
    rendered = template
    for placeholder, value in sorted(replacements.items()):
        rendered = rendered.replace("{{" + placeholder + "}}", value)
    leftover = PLACEHOLDER_PATTERN.search(rendered)
    if leftover is not None:
        msg = f"template still contains placeholder {leftover.group(0)}"
        raise SharedEdgeRenderError(msg)
    return rendered


def tls_replacements(
    config: EdgeConfiguration,
    *,
    templates_dir: Path = TEMPLATES_DIR,
) -> dict[str, str]:
    """Return the strict placeholder set for the TLS templates."""
    forecast_block = ""
    if config.forecast_hostname is not None and config.forecast_upstream is not None:
        forecast_template = (templates_dir / FORECAST_VHOST_TEMPLATE).read_text(
            encoding="utf-8",
        )
        forecast_block = render_template(
            forecast_template,
            {
                "FORECAST_HOSTNAME": config.forecast_hostname,
                "FORECAST_UPSTREAM": config.forecast_upstream,
            },
        )
        if not forecast_block.startswith("\n"):
            forecast_block = "\n" + forecast_block
        if not forecast_block.endswith("\n"):
            forecast_block += "\n"
    return {
        "CLIENT_MAX_BODY_SIZE": config.client_max_body_size,
        "FORECAST_SERVER_BLOCK": forecast_block,
        "WEF_API_UPSTREAM": config.wef_api_upstream,
        "WEF_HOSTNAME": config.wef_hostname,
        "WEF_MEDIA_UPSTREAM": config.wef_media_upstream,
        "WEF_WEB_UPSTREAM": config.wef_web_upstream,
    }


def render_issuance_commands(config: EdgeConfiguration) -> str:
    """Render the non-interactive webroot issuance commands per hostname."""
    account_flags = (
        "--register-unsafely-without-email" if config.email is None else f"--email {config.email}"
    )
    hostnames = [config.wef_hostname]
    if config.forecast_hostname is not None:
        hostnames.append(config.forecast_hostname)
    lines = [
        "# Non-interactive webroot issuance rendered by shared_edge_render.py.",
        "# Run inside the certbot service of the shared-edge project, never on the host.",
    ]
    lines.extend(
        "certbot certonly"
        " --non-interactive"
        " --agree-tos"
        f" {account_flags}"
        " --webroot"
        " -w /var/www/certbot"
        f" --cert-name {hostname}"
        f" -d {hostname}"
        f" --server {config.resolved_acme_server}"
        " --deploy-hook /edge-hooks/deploy-hook.sh"
        for hostname in sorted(hostnames)
    )
    return "\n".join(lines) + "\n"


def validate_release_dir(output_dir: Path) -> None:
    """Reject unsafe or non-deterministic release directories."""
    for fragment in FORBIDDEN_PATH_FRAGMENTS:
        if fragment in output_dir.parts:
            msg = f"release directory must not contain {fragment!r}"
            raise SharedEdgeRenderError(msg)
    if not RELEASE_NAME_PATTERN.fullmatch(output_dir.name):
        msg = "release directory name must be lowercase alphanumerics and dashes"
        raise SharedEdgeRenderError(msg)
    if len(output_dir.parts) < 2:
        msg = "release directory must not be a filesystem root"
        raise SharedEdgeRenderError(msg)
    if output_dir.exists() and any(output_dir.iterdir()):
        msg = "release directory must be new or empty for deterministic output"
        raise SharedEdgeRenderError(msg)


def write_release(
    config: EdgeConfiguration,
    output_dir: Path,
    *,
    templates_dir: Path = TEMPLATES_DIR,
) -> list[Path]:
    """Write one complete deterministic edge release and return its files."""
    validate_configuration(config)
    validate_release_dir(output_dir)
    bootstrap_template = (templates_dir / BOOTSTRAP_TEMPLATE).read_text(encoding="utf-8")
    tls_template = (templates_dir / TLS_TEMPLATE).read_text(encoding="utf-8")
    tls_redirect_template = (templates_dir / TLS_REDIRECT_TEMPLATE).read_text(encoding="utf-8")
    replacements = tls_replacements(config, templates_dir=templates_dir)
    rendered = {
        BOOTSTRAP_CONFIG: render_template(bootstrap_template, {}),
        TLS_CONFIG: render_template(tls_template, replacements),
        TLS_REDIRECT_CONFIG: render_template(tls_redirect_template, replacements),
        ISSUANCE_FILENAME: render_issuance_commands(config),
    }
    hook_source = templates_dir / HOOK_FILENAME
    output_dir.mkdir(parents=True, exist_ok=True)
    written = [output_dir / name for name in sorted(rendered)]
    for target in written:
        target.write_text(rendered[target.name], encoding="utf-8")
    hook_target = output_dir / HOOK_FILENAME
    hook_target.write_bytes(hook_source.read_bytes())
    # World-executable: hook validation runs as a capped root that does not
    # own the edge tree and therefore checks the "other" permission class.
    hook_target.chmod(0o755)
    written.append(hook_target)
    return written


def parse_configuration(argv: list[str] | None) -> tuple[EdgeConfiguration, Path, Path]:
    """Parse and validate renderer arguments into configuration and target."""
    parser = argparse.ArgumentParser(description="Render a deterministic shared-edge release.")
    parser.add_argument("--wef-hostname", required=True)
    parser.add_argument("--forecast-hostname", default=None)
    parser.add_argument("--wef-api-upstream", required=True)
    parser.add_argument("--wef-media-upstream", required=True)
    parser.add_argument("--wef-web-upstream", required=True)
    parser.add_argument("--forecast-upstream", default=None)
    parser.add_argument("--client-max-body-size", default="1m")
    parser.add_argument("--email", default=None)
    parser.add_argument("--acme-server", default=PRODUCTION_ACME_SERVER)
    parser.add_argument("--fixture-mode", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--templates-dir",
        type=Path,
        default=TEMPLATES_DIR,
    )
    arguments = parser.parse_args(argv)
    config = EdgeConfiguration(
        wef_hostname=arguments.wef_hostname,
        forecast_hostname=arguments.forecast_hostname,
        wef_api_upstream=arguments.wef_api_upstream,
        wef_media_upstream=arguments.wef_media_upstream,
        wef_web_upstream=arguments.wef_web_upstream,
        forecast_upstream=arguments.forecast_upstream,
        client_max_body_size=arguments.client_max_body_size,
        acme_server=arguments.acme_server,
        email=arguments.email,
        fixture_mode=arguments.fixture_mode,
    )
    return config, arguments.output_dir, arguments.templates_dir


def main(argv: list[str] | None = None) -> int:
    """Render one validated shared-edge release from CLI arguments."""
    config, output_dir, templates_dir = parse_configuration(argv)
    try:
        written = write_release(config, output_dir, templates_dir=templates_dir)
    except SharedEdgeRenderError as error:
        print(f"shared_edge_render: {error}", file=sys.stderr)
        return 1
    print(f"shared_edge_render: wrote {len(written)} files to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
