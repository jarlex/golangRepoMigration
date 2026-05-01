from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from migration.git_service import GitService
from migration.errors import MigrationError


class GitServiceTests(unittest.TestCase):
    def test_command_failure_is_parseable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            svc = GitService()
            with self.assertRaises(MigrationError) as ctx:
                svc.is_working_tree_clean(Path(td))
            self.assertEqual(ctx.exception.detail.code, "ERR_GIT_COMMAND_FAILED")

    def test_commit_and_tag_uses_signed_commit_flag(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo_path = Path(td)
            calls: list[list[str]] = []

            def _fake_run(cmd, cwd, text, capture_output, check):
                calls.append(list(cmd))

                class _CP:
                    returncode = 0
                    stdout = ""
                    stderr = ""

                return _CP()

            with patch("migration.git_service.subprocess.run", side_effect=_fake_run):
                GitService().commit_and_tag(repo_path=repo_path, message="chore (repo)", tag="v1.2.3")

            self.assertEqual(calls[0], ["git", "add", "-A"])
            self.assertEqual(calls[1], ["git", "commit", "-S", "-m", "chore (repo)"])
            self.assertEqual(calls[2], ["git", "tag", "v1.2.3"])


if __name__ == "__main__":
    unittest.main()
