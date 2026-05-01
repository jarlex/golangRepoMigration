from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from migration.csv_store import CsvStore, EXPECTED_HEADER
from migration.errors import MigrationError


class CsvStoreTests(unittest.TestCase):
    def test_rejects_invalid_header(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "rows.csv"
            path.write_text("a,b\n1,2\n", encoding="utf-8")
            store = CsvStore(path)
            with self.assertRaises(MigrationError) as ctx:
                store.load_rows()
            self.assertEqual(ctx.exception.detail.code, "ERR_CSV_HEADER_MISMATCH")

    def test_rejects_header_with_extra_column(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "rows.csv"
            path.write_text(
                ",".join(EXPECTED_HEADER + ["extra"])
                + "\n"
                + "bb,org/repo,old,new,v1.0.0,,,x\n",
                encoding="utf-8",
            )
            with self.assertRaises(MigrationError) as ctx:
                CsvStore(path).load_rows()
            self.assertEqual(ctx.exception.detail.code, "ERR_CSV_HEADER_MISMATCH")

    def test_rejects_missing_required_field(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "rows.csv"
            path.write_text(
                ",".join(EXPECTED_HEADER)
                + "\n"
                + "bb,org/repo,old,,v1.0.0,,\n",
                encoding="utf-8",
            )
            with self.assertRaises(MigrationError) as ctx:
                CsvStore(path).load_rows()
            self.assertEqual(ctx.exception.detail.code, "ERR_CSV_MISSING_FIELD")

    def test_updates_row_status(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "rows.csv"
            path.write_text(
                ",".join(EXPECTED_HEADER)
                + "\n"
                + "bb,org/repo,old,new,v1.0.0,,\n",
                encoding="utf-8",
            )
            store = CsvStore(path)
            store.update_row_status(2, "success", "OK")
            content = path.read_text(encoding="utf-8")
            self.assertIn(",success,OK", content)


if __name__ == "__main__":
    unittest.main()
