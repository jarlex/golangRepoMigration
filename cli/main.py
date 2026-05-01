from __future__ import annotations

import sys

from migration.config import parse_args
from migration.errors import MigrationError
from migration.orchestrator import run_batch


def main() -> int:
    try:
        config = parse_args()
        return run_batch(config)
    except MigrationError as exc:
        sys.stderr.write(exc.detail.as_parseable() + "\n")
        return int(exc.exit_code)


if __name__ == "__main__":
    sys.exit(main())
