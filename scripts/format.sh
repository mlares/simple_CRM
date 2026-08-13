#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
uv run --locked ruff check --fix .
uv run --locked ruff format .
uv run --locked djlint src/simple_crm/platform/templates --reformat
