"""E20-T1: the admin console renders with the public dark design tokens."""

from tests.test_admin_api import admin_client
from wef_backend.features.admin.interface.enrichment_views import _page
from wef_backend.features.admin.interface.mount import _THEME


def test_admin_theme_is_dark_and_primer_aligned() -> None:
    """The console renders Tabler dark with the public palette attributes."""
    assert _THEME.settings.html_attrs() == {
        "data-bs-theme": "dark",
        "data-bs-theme-base": "zinc",
        "data-bs-theme-primary": "green",
        "data-bs-theme-radius": "1",
    }


async def test_login_page_renders_dark_with_shared_stylesheet() -> None:
    """Shell pages carry the dark theme attributes and the token stylesheet."""
    async with admin_client() as (client, _store):
        page = await client.get("/admin/login")
        assert page.status_code == 200
        assert 'data-bs-theme="dark"' in page.text
        assert 'data-bs-theme-primary="green"' in page.text
        assert "css/admin.css" in page.text


async def test_shared_admin_stylesheet_serves_primer_tokens() -> None:
    """The one shared stylesheet exposes the public-site token values."""
    async with admin_client() as (client, _store):
        sheet = await client.get("/admin/static/css/admin.css?v=1")
        assert sheet.status_code == 200
        assert "--wef-canvas: #0d1117" in sheet.text
        assert "--wef-accent: #3fb950" in sheet.text
        assert '[data-bs-theme="dark"]' in sheet.text


def test_enrichment_page_shell_uses_dark_tokens() -> None:
    """Standalone pages consume the shared tokens with no light leftovers."""
    response = _page("Batches", "<p>body</p>")
    body = bytes(response.body).decode()
    assert "color-scheme:dark" in body
    assert "css/admin.css" in body
    assert "background:var(--wef-canvas)" in body
    assert "color:var(--wef-text)" in body
    assert "#fff" not in body
    assert "#ddd" not in body
    assert "color-scheme:light" not in body
