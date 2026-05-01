from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from migration.orchestrator import run_batch


HEADER = "bb_repo,gh_repo,module_old,module_new,next_tag,status,notes\n"


class OrchestratorSequentialContractTests(unittest.TestCase):
    def test_sequential_order_and_persist_before_next_row(self) -> None:
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

            event_order: list[tuple[str, int | None, str]] = []

            def _capture_event(self, **kwargs):
                event_order.append((kwargs["action"], kwargs["row"], kwargs["status"]))

            with patch("migration.preflight.PreflightService._check_gpg_signing", return_value=None), patch(
                "migration.git_service.GitService.is_working_tree_clean", return_value=True
            ), patch("migration.git_service.GitService.tag_exists", return_value=False), patch(
                "migration.rewrite_engine.RewriteEngine.apply", side_effect=["changed", "changed"]
            ), patch("migration.git_service.GitService.commit_and_tag", return_value=None), patch(
                "migration.reporter.Reporter.event", new=_capture_event
            ):
                code = run_batch(cfg)

            self.assertEqual(code, 0)
            row_events = [e for e in event_order if e[0] in {"start", "persist"}]
            self.assertEqual(
                row_events,
                [
                    ("start", 2, "running"),
                    ("persist", 2, "success"),
                    ("start", 3, "running"),
                    ("persist", 3, "success"),
                ],
            )

    def test_commit_message_uses_exact_prefix_and_repo_tail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "base"
            repo1 = base / "org" / "repo1"
            repo1.mkdir(parents=True)
            (repo1 / "go.mod").write_text("module old\n", encoding="utf-8")

            csv_path = Path(td) / "rows.csv"
            csv_path.write_text(
                HEADER + "bb,https://github.enterprise.local/org/repo1.git,old,new,v1.0.0,,\n",
                encoding="utf-8",
            )
            cfg = SimpleNamespace(csv_path=csv_path, base_dir=base, commit_prefix="migration", dry_run=False, resume=False)

            with patch("migration.preflight.PreflightService._check_gpg_signing", return_value=None), patch(
                "migration.git_service.GitService.is_working_tree_clean", return_value=True
            ), patch("migration.git_service.GitService.tag_exists", return_value=False), patch(
                "migration.git_service.GitService.commit_and_tag", return_value=None
            ) as commit_mock:
                code = run_batch(cfg)

            self.assertEqual(code, 0)
            kwargs = commit_mock.call_args.kwargs
            self.assertEqual(kwargs["message"], "migration (repo1)")


if __name__ == "__main__":
    unittest.main()
