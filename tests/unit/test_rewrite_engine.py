from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from migration.models import Row
from migration.rewrite_engine import RewriteEngine


class RewriteEngineTests(unittest.TestCase):
    def test_rewrites_module_reference(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "go.mod").write_text("module github.com/a/old\n", encoding="utf-8")
            row = Row(2, "bb", "org/repo", "github.com/a/old", "github.com/a/new", "v1", "", "")
            status = RewriteEngine().apply(repo, row, dry_run=False)
            self.assertEqual(status, "changed")
            self.assertIn("github.com/a/new", (repo / "go.mod").read_text(encoding="utf-8"))

    def test_returns_already_applied_when_old_absent_and_new_present(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "go.mod").write_text("module github.com/a/new\n", encoding="utf-8")
            row = Row(2, "bb", "org/repo", "github.com/a/old", "github.com/a/new", "v1", "", "")
            status = RewriteEngine().apply(repo, row, dry_run=False)
            self.assertEqual(status, "already_applied")


if __name__ == "__main__":
    unittest.main()
