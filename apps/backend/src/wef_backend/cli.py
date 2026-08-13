"""Backend command-line entry points."""

import uvicorn

from wef_backend.settings import load_settings


def serve() -> None:
    """Run Uvicorn with an application factory."""
    settings = load_settings()
    uvicorn.run(
        "wef_backend.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )
