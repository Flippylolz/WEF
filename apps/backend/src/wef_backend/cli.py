"""Backend command-line entry points."""

import uvicorn

from wef_backend.settings import load_settings


def serve() -> None:
    """Run Uvicorn with an application factory."""
    settings = load_settings()
    # Behind the shared Nginx edge, honor X-Forwarded-Proto/For from any
    # private Docker peer. The API is not publicly published.
    forwarded_allow_ips = "*" if settings.env == "production" else "127.0.0.1"
    uvicorn.run(
        "wef_backend.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        proxy_headers=True,
        forwarded_allow_ips=forwarded_allow_ips,
    )
