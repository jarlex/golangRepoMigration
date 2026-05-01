#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  printf '%s\n' 'ERR_TEST_PYTHON_MISSING|message=python3_or_python_not_found' >&2
  exit 127
fi

"${PYTHON_BIN}" -m unittest discover -s tests/unit -p "test_*.py"
"${PYTHON_BIN}" -m unittest discover -s tests/integration -p "test_*.py"
