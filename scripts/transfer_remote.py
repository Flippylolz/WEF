"""CLI for historical transfer remote planning and server dry-run."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path

from scripts.transfer.remote_paths import DEFAULT_WEF_ROOT
from scripts.transfer.rsync_transfer import RsyncOptions, RsyncTarget, build_rsync_command
from scripts.transfer.server_dry_run import evaluate_server_dry_run, load_server_inventory
from scripts.transfer.transfer_plan import build_transfer_plan


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Historical transfer remote tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="Build one verified bundle transfer plan")
    plan.add_argument("bundle_dir", type=Path)
    plan.add_argument("--wef-root", type=Path, default=Path(DEFAULT_WEF_ROOT))

    server_dry_run = subparsers.add_parser(
        "server-dry-run",
        help="Evaluate one server inventory against a transfer plan",
    )
    server_dry_run.add_argument("bundle_dir", type=Path)
    server_dry_run.add_argument("inventory", type=Path)
    server_dry_run.add_argument("--candidate-database", required=True)
    server_dry_run.add_argument("--existing-databases", default="")
    server_dry_run.add_argument("--incoming-exists", action="store_true")
    server_dry_run.add_argument("--wef-root", type=Path, default=Path(DEFAULT_WEF_ROOT))

    rsync_plan = subparsers.add_parser("rsync-plan", help="Render one rsync transfer command")
    rsync_plan.add_argument("bundle_dir", type=Path)
    rsync_plan.add_argument("--remote-user", default="nuc")
    rsync_plan.add_argument("--remote-host", required=True)
    rsync_plan.add_argument("--ssh-port", type=int, default=22)
    rsync_plan.add_argument("--identity-file", type=Path)
    rsync_plan.add_argument("--known-hosts-file", type=Path)
    rsync_plan.add_argument("--dry-run", action="store_true")
    rsync_plan.add_argument("--wef-root", type=Path, default=Path(DEFAULT_WEF_ROOT))

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one transfer remote subcommand."""
    arguments = _build_parser().parse_args(argv)

    if arguments.command == "plan":
        plan = build_transfer_plan(
            bundle_dir=arguments.bundle_dir,
            wef_root=arguments.wef_root,
        )
        payload = {
            "bundle_checksum": plan.bundle_checksum,
            "migration_head": plan.migration_head,
            "remote_incoming_dir": str(plan.remote_incoming_dir),
            "remote_extracted_dir": str(plan.remote_extracted_dir),
            "total_bytes": plan.total_bytes,
            "components": [
                {
                    "name": component.name,
                    "size_bytes": component.size_bytes,
                    "sha256": component.sha256,
                }
                for component in plan.components
            ],
        }
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return 0

    if arguments.command == "server-dry-run":
        plan = build_transfer_plan(
            bundle_dir=arguments.bundle_dir,
            wef_root=arguments.wef_root,
        )
        inventory = load_server_inventory(arguments.inventory)
        existing = tuple(
            item.strip() for item in arguments.existing_databases.split(",") if item.strip()
        )
        summary = evaluate_server_dry_run(
            plan=plan,
            inventory=inventory,
            candidate_database=arguments.candidate_database,
            existing_databases=existing,
            incoming_exists=arguments.incoming_exists,
        )
        payload = {
            "allowed": summary.allowed,
            "refusal_reasons": list(summary.refusal_reasons),
            "bundle_bytes": summary.bundle_bytes,
            "available_disk_bytes": summary.available_disk_bytes,
            "minimum_headroom_bytes": summary.minimum_headroom_bytes,
            "migration_head": summary.migration_head,
            "candidate_database": summary.candidate_database,
        }
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return 0 if summary.allowed else 1

    plan = build_transfer_plan(
        bundle_dir=arguments.bundle_dir,
        wef_root=arguments.wef_root,
    )
    command = build_rsync_command(
        local_bundle_dir=arguments.bundle_dir,
        remote_incoming_dir=plan.remote_incoming_dir,
        target=RsyncTarget(
            user=arguments.remote_user,
            host=arguments.remote_host,
            port=arguments.ssh_port,
        ),
        options=RsyncOptions(
            identity_file=arguments.identity_file,
            known_hosts_file=arguments.known_hosts_file,
            dry_run=arguments.dry_run,
        ),
    )
    sys.stdout.write(shlex.join(command) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
