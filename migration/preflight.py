from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from migration.errors import preflight_error
from migration.git_service import GitService
from migration.models import Row


class PreflightService:
    def __init__(self, git: GitService):
        self.git = git

    def run_global(self, rows: list[Row], base_dir: Path) -> None:
        self._check_gpg_signing()
        for row in rows:
            repo_path = self._derive_repo_path(base_dir, row.gh_repo)
            if not repo_path.exists() or not repo_path.is_dir():
                raise preflight_error(
                    "REPO_NOT_FOUND",
                    f"local repo not found: {repo_path}",
                    row=row.row_number,
                    repo=row.gh_repo,
                )
            if not self.git.is_working_tree_clean(repo_path):
                raise preflight_error(
                    "DIRTY_TREE",
                    "working tree is not clean",
                    row=row.row_number,
                    repo=row.gh_repo,
                )
            if self.git.tag_exists(repo_path, row.next_tag):
                raise preflight_error(
                    "TAG_EXISTS",
                    f"tag already exists: {row.next_tag}",
                    row=row.row_number,
                    repo=row.gh_repo,
                )

    @staticmethod
    def _derive_repo_path(base_dir: Path, gh_repo: str) -> Path:
        normalized = gh_repo.strip().replace("https://", "").replace("http://", "")
        if normalized.endswith(".git"):
            normalized = normalized[:-4]
        parts = [p for p in normalized.split("/") if p]
        if len(parts) < 2:
            raise preflight_error("INVALID_GH_REPO", f"cannot derive org/repo from gh_repo={gh_repo}")
        org, repo = parts[-2], parts[-1]
        return base_dir / org / repo

    @staticmethod
    def _check_gpg_signing() -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            PreflightService._run(["git", "init"], cwd=repo)
            PreflightService._run(["git", "config", "user.email", "migration-check@example.local"], cwd=repo)
            PreflightService._run(["git", "config", "user.name", "Migration Check"], cwd=repo)
            marker = repo / "marker.txt"
            marker.write_text("gpg-check\n", encoding="utf-8")
            PreflightService._run(["git", "add", "marker.txt"], cwd=repo)
            PreflightService._run(
                ["git", "-c", "commit.gpgsign=true", "commit", "-S", "-m", "gpg-preflight"],
                cwd=repo,
            )

    @staticmethod
    def _run(cmd: list[str], cwd: Path) -> None:
        cp = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=False)
        if cp.returncode != 0:
            stderr = (cp.stderr or "").strip()
            raise preflight_error("GPG_UNAVAILABLE", f"cmd={' '.join(cmd)} stderr={stderr}")
