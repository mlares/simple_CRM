#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VERIFY_PARENT="${TMPDIR:-/tmp}"
case "$VERIFY_PARENT" in
  /*) ;;
  *)
    echo "TMPDIR must be an absolute path" >&2
    exit 2
    ;;
esac

VERIFY_TMP_DIR="$(mktemp -d "${VERIFY_PARENT%/}/simple-crm-verify.XXXXXXXX")"
case "$VERIFY_TMP_DIR" in
  "${VERIFY_PARENT%/}"/simple-crm-verify.*) ;;
  *)
    echo "Refusing an unexpected temporary directory" >&2
    exit 2
    ;;
esac

cleanup() {
  case "$VERIFY_TMP_DIR" in
    "${VERIFY_PARENT%/}"/simple-crm-verify.*)
      rm -rf -- "$VERIFY_TMP_DIR"
      ;;
    *)
      echo "Refusing to clean an unexpected path" >&2
      return 1
      ;;
  esac
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

cd "$PROJECT_ROOT"
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
export UV_PROJECT_ENVIRONMENT="$VERIFY_TMP_DIR/.venv"
export UV_OFFLINE=1
export PYTHONDONTWRITEBYTECODE=1

uv sync --locked --all-groups --offline
"$PROJECT_ROOT/scripts/verify-fast.sh"
