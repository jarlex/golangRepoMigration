from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from migration.errors import csv_error, persistence_error
from migration.models import Row


EXPECTED_HEADER = [
    "bb_repo",
    "gh_repo",
    "module_old",
    "module_new",
    "next_tag",
    "status",
    "notes",
]


class CsvStore:
    def __init__(self, csv_path: Path):
        self.csv_path = csv_path

    def load_rows(self) -> list[Row]:
        with self.csv_path.open("r", encoding="utf-8", newline="") as fp:
            reader = csv.DictReader(fp)
            header = reader.fieldnames or []
            if header != EXPECTED_HEADER:
                raise csv_error(
                    "HEADER_MISMATCH",
                    f"expected header={','.join(EXPECTED_HEADER)} got={','.join(header)}",
                )

            rows: list[Row] = []
            for row_number, raw in enumerate(reader, start=2):
                self._validate_row(raw, row_number)
                rows.append(
                    Row(
                        row_number=row_number,
                        bb_repo=raw["bb_repo"].strip(),
                        gh_repo=raw["gh_repo"].strip(),
                        module_old=raw["module_old"].strip(),
                        module_new=raw["module_new"].strip(),
                        next_tag=raw["next_tag"].strip(),
                        status=raw["status"].strip(),
                        notes=raw["notes"].strip(),
                    )
                )
            return rows

    def update_row_status(self, target_row_number: int, status: str, notes: str) -> None:
        with self.csv_path.open("r", encoding="utf-8", newline="") as fp:
            reader = csv.DictReader(fp)
            header = reader.fieldnames or []
            if header != EXPECTED_HEADER:
                raise persistence_error("CSV_HEADER_DRIFT", "csv header drift detected while updating state")
            buffer: list[dict[str, str]] = [dict(row) for row in reader]

        idx = target_row_number - 2
        if idx < 0 or idx >= len(buffer):
            raise persistence_error("ROW_INDEX_OUT_OF_RANGE", f"cannot update row {target_row_number}")

        buffer[idx]["status"] = status
        buffer[idx]["notes"] = notes

        with self.csv_path.open("w", encoding="utf-8", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=EXPECTED_HEADER)
            writer.writeheader()
            writer.writerows(buffer)

    @staticmethod
    def _validate_row(raw: dict[str, str], row_number: int) -> None:
        required = ["bb_repo", "gh_repo", "module_old", "module_new", "next_tag"]
        for key in required:
            if not raw.get(key, "").strip():
                raise csv_error("MISSING_FIELD", f"field '{key}' is required", row=row_number)

        gh = raw["gh_repo"].strip()
        parts = [p for p in gh.split("/") if p]
        if len(parts) < 2:
            raise csv_error("INVALID_GH_REPO", f"gh_repo must be org/repo format: {gh}", row=row_number)
