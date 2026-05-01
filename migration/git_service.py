from __future__ import annotations

import subprocess
from pathlib import Path

from migration.errors import git_error


class GitService:
    def is_working_tree_clean(self, repo_path: Path) -> bool:
        cp = self._run(["git", "status", "--porcelain"], cwd=repo_path)
        return cp.stdout.strip() == ""

    def tag_exists(self, repo_path: Path, tag: str) -> bool:
        cp = self._run(["git", "tag", "-l", tag], cwd=repo_path)
        return cp.stdout.strip() == tag

    def commit_and_tag(self, repo_path: Path, message: str, tag: str) -> None:
        self._run(["git", "add", "-A"], cwd=repo_path)
        self._run(["git", "commit", "-S", "-m", message], cwd=repo_path)
        self._run(["git", "tag", tag], cwd=repo_path)

    @staticmethod
    def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        cp = subprocess.run(
            cmd,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            check=False,
        )
        if cp.returncode != 0:
            stderr = (cp.stderr or "").strip()
            raise git_error("COMMAND_FAILED", f"cmd={' '.join(cmd)} stderr={stderr}")
        return cp
