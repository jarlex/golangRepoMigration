from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from migration.orchestrator import run_batch


HEADER = "bb_repo,gh_repo,module_old,module_new,next_tag,status,notes\n"


class OrchestratorDryRunTests(unittest.TestCase):
    def test_dry_run_does_not_mutate_csv(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "base"
            repo = base / "org" / "repo"
            repo.mkdir(parents=True)
            (repo / "go.mod").write_text("module old\n", encoding="utf-8")

            csv_path = Path(td) / "rows.csv"
            original = HEADER + "bb,org/repo,old,new,v1.0.0,,\n"
            csv_path.write_text(original, encoding="utf-8")
            original_go_mod = (repo / "go.mod").read_text(encoding="utf-8")
            cfg = SimpleNamespace(csv_path=csv_path, base_dir=base, commit_prefix="chore", dry_run=True, resume=False)

            with patch("migration.preflight.PreflightService._check_gpg_signing", return_value=None), patch(
                "migration.git_service.GitService.is_working_tree_clean", return_value=True
            ), patch("migration.git_service.GitService.tag_exists", return_value=False), patch(
                "migration.git_service.GitService.commit_and_tag", side_effect=AssertionError("commit/tag must not run in dry-run")
            ), patch(
                "migration.csv_store.CsvStore.update_row_status", side_effect=AssertionError("csv status must not mutate in dry-run")
            ):
                code = run_batch(cfg)

            self.assertEqual(code, 0)
            self.assertEqual(csv_path.read_text(encoding="utf-8"), original)
            self.assertEqual((repo / "go.mod").read_text(encoding="utf-8"), original_go_mod)


if __name__ == "__main__":
    unittest.main()
