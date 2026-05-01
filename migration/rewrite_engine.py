from __future__ import annotations

from pathlib import Path

from migration.errors import rewrite_error
from migration.models import Row


class RewriteEngine:
    def apply(self, repo_path: Path, row: Row, dry_run: bool) -> str:
        targets = self._candidate_files(repo_path)
        touched = 0
        already_applied = True
        for file_path in targets:
            try:
                original = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if row.module_old in original:
                already_applied = False
                updated = original.replace(row.module_old, row.module_new)
                if updated != original:
                    touched += 1
                    if not dry_run:
                        file_path.write_text(updated, encoding="utf-8")
            elif row.module_new not in original:
                already_applied = False

        if touched > 0:
            return "changed"
        if already_applied:
            return "already_applied"
        return "no_changes"

    @staticmethod
    def _candidate_files(repo_path: Path) -> list[Path]:
        try:
            files = [
                p
                for p in repo_path.rglob("*")
                if p.is_file() and p.suffix in {".go", ".mod", ".sum", ".txt", ".md", ""}
            ]
            return files
        except OSError as exc:
            raise rewrite_error("SCAN_FAILED", f"failed to scan repository: {exc}") from exc
