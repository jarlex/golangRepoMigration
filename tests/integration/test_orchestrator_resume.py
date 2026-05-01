from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from migration.orchestrator import run_batch


HEADER = "bb_repo,gh_repo,module_old,module_new,next_tag,status,notes\n"


class OrchestratorResumeTests(unittest.TestCase):
    def test_resume_skips_terminal_rows(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "base"
            repo = base / "org" / "repo2"
            repo.mkdir(parents=True)
            (repo / "go.mod").write_text("module old\n", encoding="utf-8")

            csv_path = Path(td) / "rows.csv"
            csv_path.write_text(
                HEADER
                + "bb,org/repo1,old,new,v1.0.0,success,done\n"
                + "bb,org/repo2,old,new,v1.0.1,,\n",
                encoding="utf-8",
            )
            cfg = SimpleNamespace(csv_path=csv_path, base_dir=base, commit_prefix="chore", dry_run=True, resume=True)

            with patch("migration.preflight.PreflightService._check_gpg_signing", return_value=None), patch(
                "migration.git_service.GitService.is_working_tree_clean", return_value=True
            ), patch("migration.git_service.GitService.tag_exists", return_value=False):
                code = run_batch(cfg)

            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
