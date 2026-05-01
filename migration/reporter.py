from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class Reporter:
    def __init__(self, logs_dir: Path):
        self.run_id = uuid4().hex
        logs_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = logs_dir / f"migration-{self.run_id}.jsonl"
        self._start_ns = time.time_ns()

    @property
    def log_path(self) -> Path:
        return self._log_path

    def event(
        self,
        *,
        level: str,
        row: int | None,
        gh_repo: str | None,
        phase: str,
        action: str,
        status: str,
        code: str,
        message: str,
    ) -> None:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "run_id": self.run_id,
            "row": row,
            "gh_repo": gh_repo,
            "phase": phase,
            "action": action,
            "status": status,
            "code": code,
            "message": message,
            "duration_ms": int((time.time_ns() - self._start_ns) / 1_000_000),
        }
        line = json.dumps(payload, ensure_ascii=False)
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
        with self._log_path.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")

    def summary(self, *, exit_code: int, failed_row: int | None, failed_code: str | None) -> None:
        self.event(
            level="info" if exit_code == 0 else "error",
            row=failed_row,
            gh_repo=None,
            phase="summary",
            action="finish",
            status="ok" if exit_code == 0 else "error",
            code=failed_code or "OK",
            message=f"exit_code={exit_code}|failed_row={failed_row}|failed_code={failed_code}",
        )
