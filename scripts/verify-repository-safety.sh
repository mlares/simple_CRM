#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if rg -n --hidden --glob '!.git/**' --glob '!.venv/**' --glob '!uv.lock' \
  '(-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9_]{20,})' .; then
  echo "repository safety scan found a credential-like value" >&2
  exit 1
fi
if find . -type f \( -name '*.env' -o -name '.env.*' \) ! -name '.env.example' -print -quit | grep -q .; then
  echo "repository safety scan found a local environment file" >&2
  exit 1
fi
echo "repository safety scan passed"
