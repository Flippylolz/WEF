"""Build a mode-0600 candidate verification environment from CI inputs."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.deploy.build_release_config import required_environment, write_environment
from scripts.deploy.candidate_config import (
    CandidateContext,
    build_candidate_values,
)


def main() -> int:
    """Build one complete candidate verification configuration."""
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("root", type=Path)
    parser.add_argument("bundle_checksum")
    parser.add_argument("candidate_database")
    parser.add_argument("backend_image")
    parser.add_argument("web_image")
    parser.add_argument("--verify-port", type=int, default=13100)
    parser.add_argument("--test-mode", action="store_true")
    arguments = parser.parse_args()

    values = build_candidate_values(
        context=CandidateContext(
            root=arguments.root,
            bundle_checksum=arguments.bundle_checksum,
            candidate_database=arguments.candidate_database,
            backend_image=arguments.backend_image,
            web_image=arguments.web_image,
            verify_port=arguments.verify_port,
            test_mode=arguments.test_mode,
        ),
        postgres_user=required_environment("POSTGRES_USER"),
        postgres_password=required_environment("POSTGRES_PASSWORD"),
    )
    write_environment(arguments.output, values)
    print("Complete candidate configuration created with mode 0600.")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
