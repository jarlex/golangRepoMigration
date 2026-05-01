from __future__ import annotations

from pathlib import Path

from migration.csv_store import CsvStore
from migration.errors import MigrationError, git_error, preflight_error, rewrite_error
from migration.git_service import GitService
from migration.models import ExitCode, Row, TERMINAL_STATUSES
from migration.preflight import PreflightService
from migration.reporter import Reporter
from migration.rewrite_engine import RewriteEngine


def run_batch(config) -> int:
    reporter = Reporter(logs_dir=Path("logs"))
    store = CsvStore(config.csv_path)
    git = GitService()
    preflight = PreflightService(git=git)
    engine = RewriteEngine()

    try:
        rows = store.load_rows()
        planned_rows = _rows_for_execution(rows, config.resume)
        preflight.run_global(planned_rows, config.base_dir)
        for row in planned_rows:
            _process_row(row=row, config=config, store=store, git=git, engine=engine, reporter=reporter)
        reporter.summary(exit_code=0, failed_row=None, failed_code=None)
        return int(ExitCode.OK)
    except MigrationError as exc:
        if exc.detail.row is not None:
            try:
                if not config.dry_run:
                    store.update_row_status(exc.detail.row, "error", exc.detail.as_parseable())
            except MigrationError:
                pass
        reporter.event(
            level="error",
            row=exc.detail.row,
            gh_repo=exc.detail.repo,
            phase="batch",
            action="abort",
            status="error",
            code=exc.detail.code,
            message=exc.detail.as_parseable(),
        )
        reporter.summary(
            exit_code=int(exc.exit_code),
            failed_row=exc.detail.row,
            failed_code=exc.detail.code,
        )
        return int(exc.exit_code)


def _rows_for_execution(rows: list[Row], resume: bool) -> list[Row]:
    if not resume:
        return rows
    start = 0
    for idx, row in enumerate(rows):
        if row.status.strip() not in TERMINAL_STATUSES:
            start = idx
            break
    else:
        return []
    return rows[start:]


def _process_row(row, config, store, git, engine, reporter) -> None:
    repo_path = PreflightService._derive_repo_path(config.base_dir, row.gh_repo)

    reporter.event(
        level="info",
        row=row.row_number,
        gh_repo=row.gh_repo,
        phase="row",
        action="start",
        status="running",
        code="OK",
        message="processing row",
    )

    try:
        rewrite_status = engine.apply(repo_path=repo_path, row=row, dry_run=config.dry_run)
    except MigrationError:
        raise
    except Exception as exc:
        raise rewrite_error("UNEXPECTED", f"unexpected row execution error: {exc}", row=row.row_number, repo=row.gh_repo) from exc
    if config.dry_run:
        reporter.event(
            level="info",
            row=row.row_number,
            gh_repo=row.gh_repo,
            phase="row",
            action="plan",
            status=rewrite_status,
            code="OK",
            message="dry-run no mutations",
        )
        return

    if rewrite_status == "changed":
        repo_tail = _repo_tail(row.gh_repo)
        message = f"{config.commit_prefix} ({repo_tail})"
        try:
            git.commit_and_tag(repo_path=repo_path, message=message, tag=row.next_tag)
        except MigrationError:
            raise
        except Exception as exc:
            raise git_error("COMMIT_TAG_FAILED", f"unexpected git error: {exc}", row=row.row_number, repo=row.gh_repo) from exc
        status = "success"
        notes = "OK|message=changed_committed_and_tagged"
    elif rewrite_status == "already_applied":
        status = "already_applied"
        notes = "OK|message=already_applied"
    else:
        status = "no_changes"
        notes = "OK|message=no_changes"

    store.update_row_status(row.row_number, status, notes)
    reporter.event(
        level="info",
        row=row.row_number,
        gh_repo=row.gh_repo,
        phase="row",
        action="persist",
        status=status,
        code="OK",
        message=notes,
    )


def _repo_tail(gh_repo: str) -> str:
    normalized = gh_repo.strip().rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    parts = [p for p in normalized.split("/") if p]
    if not parts:
        raise preflight_error("INVALID_GH_REPO", f"cannot parse repo tail from {gh_repo}")
    return parts[-1]
