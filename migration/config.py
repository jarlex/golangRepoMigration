from __future__ import annotations

import argparse
from pathlib import Path

from migration.errors import csv_error
from migration.models import RunConfig


def parse_args() -> RunConfig:
    parser = argparse.ArgumentParser(description="Local strict Go modules migration CLI")
    parser.add_argument("--csv", required=True, dest="csv_path", help="Path to migration CSV")
    parser.add_argument("--base-dir", required=True, dest="base_dir", help="Base directory with local repos")
    parser.add_argument("--commit-prefix", required=True, dest="commit_prefix", help="Commit prefix for message format")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, no mutations")
    parser.add_argument("--resume", action="store_true", help="Skip terminal rows and continue")

    args = parser.parse_args()

    csv_path = Path(args.csv_path).expanduser().resolve()
    base_dir = Path(args.base_dir).expanduser().resolve()
    prefix = str(args.commit_prefix).strip()

    if not csv_path.exists() or not csv_path.is_file():
        raise csv_error("CSV_NOT_FOUND", f"csv file not found: {csv_path}")
    if not base_dir.exists() or not base_dir.is_dir():
        raise csv_error("BASE_DIR_NOT_FOUND", f"base-dir not found: {base_dir}")
    if not prefix:
        raise csv_error("INVALID_COMMIT_PREFIX", "commit-prefix cannot be empty")

    return RunConfig(
        csv_path=csv_path,
        base_dir=base_dir,
        commit_prefix=prefix,
        dry_run=bool(args.dry_run),
        resume=bool(args.resume),
    )
