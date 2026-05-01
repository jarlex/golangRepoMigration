from __future__ import annotations

from dataclasses import dataclass

from migration.models import ErrorDetail, ExitCode


@dataclass(frozen=True)
class MigrationError(Exception):
    detail: ErrorDetail
    exit_code: ExitCode

    def __str__(self) -> str:
        return self.detail.as_parseable()


def csv_error(code_suffix: str, message: str, row: int | None = None, repo: str | None = None) -> MigrationError:
    return MigrationError(
        detail=ErrorDetail(code=f"ERR_CSV_{code_suffix}", message=message, row=row, repo=repo),
        exit_code=ExitCode.CSV_CONTRACT,
    )


def preflight_error(code_suffix: str, message: str, row: int | None = None, repo: str | None = None) -> MigrationError:
    return MigrationError(
        detail=ErrorDetail(code=f"ERR_PREFLIGHT_{code_suffix}", message=message, row=row, repo=repo),
        exit_code=ExitCode.PREFLIGHT,
    )


def rewrite_error(code_suffix: str, message: str, row: int | None = None, repo: str | None = None) -> MigrationError:
    return MigrationError(
        detail=ErrorDetail(code=f"ERR_REWRITE_{code_suffix}", message=message, row=row, repo=repo),
        exit_code=ExitCode.REWRITE,
    )


def git_error(code_suffix: str, message: str, row: int | None = None, repo: str | None = None) -> MigrationError:
    return MigrationError(
        detail=ErrorDetail(code=f"ERR_GIT_{code_suffix}", message=message, row=row, repo=repo),
        exit_code=ExitCode.GIT,
    )


def persistence_error(code_suffix: str, message: str, row: int | None = None, repo: str | None = None) -> MigrationError:
    return MigrationError(
        detail=ErrorDetail(code=f"ERR_PERSIST_{code_suffix}", message=message, row=row, repo=repo),
        exit_code=ExitCode.PERSISTENCE,
    )
