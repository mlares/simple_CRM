#!/usr/bin/env bash
# Provider-neutral harness validation and optional project verification.
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT_DIR"

python3 scripts/harness_check.py

TEST_COMMAND=$(python3 -c \
  'import json; print(json.load(open("harness.json", encoding="utf-8"))["test_command"])')

if [ -n "$TEST_COMMAND" ]; then
  echo "[harness] running configured verification command"
  sh -c "$TEST_COMMAND"
else
  echo "[harness] no test_command configured; contract checks passed"
fi

echo "[harness] ready"
