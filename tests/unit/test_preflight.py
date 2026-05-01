from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from migration.git_service import GitService
from migration.models import Row
from migration.preflight import PreflightService
from migration.errors import MigrationError


class _GitFake(GitService):
    def is_working_tree_clean(self, repo_path: Path) -> bool:
        return True

    def tag_exists(self, repo_path: Path, tag: str) -> bool:
        return False


class PreflightTests(unittest.TestCase):
    def test_repo_not_found_fails(self) -> None:
        row = Row(2, "bb", "org/missing", "old", "new", "v1", "", "")
        svc = PreflightService(git=_GitFake())
        with patch("migration.preflight.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "true\n"
            with self.assertRaises(MigrationError) as ctx:
                svc.run_global([row], Path("/tmp/does-not-exist"))
            self.assertEqual(ctx.exception.detail.code, "ERR_PREFLIGHT_REPO_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
