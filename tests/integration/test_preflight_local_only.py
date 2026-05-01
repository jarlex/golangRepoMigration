from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from migration.errors import MigrationError
from migration.git_service import GitService
from migration.models import Row
from migration.preflight import PreflightService


class _GitFake(GitService):
    def is_working_tree_clean(self, repo_path: Path) -> bool:
        return True

    def tag_exists(self, repo_path: Path, tag: str) -> bool:
        return False


class PreflightLocalOnlyTests(unittest.TestCase):
    def test_run_global_never_calls_remote_git_network_commands(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "base"
            repo = base / "org" / "repo"
            repo.mkdir(parents=True)

            rows = [
                Row(
                    row_number=2,
                    bb_repo="bb",
                    gh_repo="org/repo",
                    module_old="old",
                    module_new="new",
                    next_tag="v1.0.0",
                    status="",
                    notes="",
                )
            ]

            seen_cmds: list[list[str]] = []

            def _capture_run(cmd: list[str], cwd: Path):
                seen_cmds.append(list(cmd))

            with patch("migration.preflight.PreflightService._run", side_effect=_capture_run):
                PreflightService(git=_GitFake()).run_global(rows, base)

            flattened = [" ".join(cmd) for cmd in seen_cmds]
            self.assertTrue(flattened)
            for command in flattened:
                self.assertNotIn(" clone", f"remote op detected: {command}")
                self.assertNotIn(" fetch", f"remote op detected: {command}")
                self.assertNotIn(" pull", f"remote op detected: {command}")

    def test_invalid_gh_repo_is_parseable_error(self) -> None:
        with self.assertRaises(MigrationError) as ctx:
            PreflightService._derive_repo_path(Path("/tmp/base"), "invalid")

        self.assertEqual(ctx.exception.detail.code, "ERR_PREFLIGHT_INVALID_GH_REPO")
        self.assertEqual(
            ctx.exception.detail.as_parseable(),
            "ERR_PREFLIGHT_INVALID_GH_REPO|message=cannot derive org/repo from gh_repo=invalid",
        )


if __name__ == "__main__":
    unittest.main()
