from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Optional


class ExitCode(IntEnum):
    OK = 0
    CSV_CONTRACT = 10
    PREFLIGHT = 20
    REWRITE = 30
    GIT = 40
    PERSISTENCE = 50


TERMINAL_STATUSES = {"success", "no_changes", "already_applied", "error"}


@dataclass(frozen=True)
class Row:
    row_number: int
    bb_repo: str
    gh_repo: str
    module_old: str
    module_new: str
    next_tag: str
    status: str
    notes: str


@dataclass(frozen=True)
class RunConfig:
    csv_path: Path
    base_dir: Path
    commit_prefix: str
    dry_run: bool
    resume: bool


@dataclass(frozen=True)
class ErrorDetail:
    code: str
    message: str
    row: Optional[int] = None
    repo: Optional[str] = None

    def as_parseable(self) -> str:
        parts = [self.code, f"message={self.message}"]
        if self.row is not None:
            parts.append(f"row={self.row}")
        if self.repo is not None:
            parts.append(f"repo={self.repo}")
        return "|".join(parts)


@dataclass(frozen=True)
class RowResult:
    status: str
    notes: str
    changed: bool = False
