from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from migration.errors import preflight_error
from migration.orchestrator import run_batch


HEADER = "bb_repo,gh_repo,module_old,module_new,next_tag,status,notes\n"


class OrchestratorFailFastTests(unittest.TestCase):
    def test_stops_on_first_error_and_persists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "base"
            repo1 = base / "org" / "repo1"
            repo2 = base / "org" / "repo2"
            repo1.mkdir(parents=True)
            repo2.mkdir(parents=True)
            (repo1 / "go.mod").write_text("module old\n", encoding="utf-8")
            (repo2 / "go.mod").write_text("module old\n", encoding="utf-8")

            csv_path = Path(td) / "rows.csv"
            csv_path.write_text(
                HEADER
                + "bb,org/repo1,old,new,v1.0.0,,\n"
                + "bb,org/repo2,old,new,v1.0.1,,\n",
                encoding="utf-8",
            )
            cfg = SimpleNamespace(csv_path=csv_path, base_dir=base, commit_prefix="chore", dry_run=False, resume=False)

            with patch("migration.preflight.PreflightService._check_gpg_signing", return_value=None), patch(
                "migration.git_service.GitService.is_working_tree_clean", return_value=True
            ), patch("migration.git_service.GitService.tag_exists", return_value=False), patch(
                "migration.git_service.GitService.commit_and_tag",
                side_effect=[Exception("boom"), None],
            ):
                code = run_batch(cfg)

            self.assertNotEqual(code, 0)
            content = csv_path.read_text(encoding="utf-8")
            self.assertIn("error", content)
            self.assertIn("ERR_GIT_COMMIT_TAG_FAILED|message=unexpected git error: boom|row=2|repo=org/repo1", content)
            self.assertIn(",org/repo2,old,new,v1.0.1,,", content)

    def test_gpg_unavailable_fails_preflight_before_row_processing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "base"
            repo = base / "org" / "repo1"
            repo.mkdir(parents=True)
            (repo / "go.mod").write_text("module old\n", encoding="utf-8")

            csv_path = Path(td) / "rows.csv"
            original = HEADER + "bb,org/repo1,old,new,v1.0.0,,\n"
            csv_path.write_text(original, encoding="utf-8")
            cfg = SimpleNamespace(csv_path=csv_path, base_dir=base, commit_prefix="chore", dry_run=False, resume=False)

            with patch(
                "migration.preflight.PreflightService._check_gpg_signing",
                side_effect=preflight_error("GPG_UNAVAILABLE", "gpg signing unavailable"),
            ), patch("migration.git_service.GitService.commit_and_tag") as commit_mock:
                code = run_batch(cfg)

            self.assertEqual(code, 20)
            self.assertFalse(commit_mock.called)
            self.assertEqual(csv_path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
