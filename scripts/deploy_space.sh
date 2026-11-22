#!/usr/bin/env bash
# Publishes apps/api to a Hugging Face Space (Docker). Idempotent.
# Requires the `hf` CLI (or `uvx`, used as fallback) and `hf auth login` with a write token.
# Usage: ./scripts/deploy_space.sh          (HF_USER and SPACE_NAME can override the defaults)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SPACE_NAME="${SPACE_NAME:-contraponto}"

if command -v hf >/dev/null 2>&1; then
  hf() { command hf "$@"; }
elif command -v uvx >/dev/null 2>&1; then
  hf() { uvx -q --from huggingface_hub hf "$@"; }
else
  echo "CLI 'hf' não encontrado. Rode: pip install -U huggingface_hub" >&2
  exit 1
fi

WHOAMI="$(hf auth whoami 2>/dev/null | grep -v '^Hint' | head -n1 || true)"
if [ -z "$WHOAMI" ] || echo "$WHOAMI" | grep -qi "not logged"; then
  echo "Faça login primeiro: hf auth login (token com permissão de escrita)" >&2
  exit 1
fi
# whoami prints "user=<name>" (newer CLI) or "<name>" (older CLI)
DETECTED="$(echo "$WHOAMI" | sed -E 's/^user=//; s/^user: *//; s/[[:space:]].*$//')"
HF_USER="${HF_USER:-$DETECTED}"
REPO="${HF_USER}/${SPACE_NAME}"
echo "Space: ${REPO}"

hf repos create "${REPO}" --type space --sdk docker --exist-ok >/dev/null

hf upload "${REPO}" "$ROOT/apps/api" . --repo-type space \
  --exclude ".venv/*" --exclude "**/__pycache__/*" --exclude ".data/*" \
  --exclude ".pytest_cache/*" --exclude ".ruff_cache/*" --exclude "tests/*" \
  --commit-message "deploy $(cd "$ROOT" && git rev-parse --short HEAD)"

SUB="$(echo "${HF_USER}-${SPACE_NAME}" | tr '[:upper:]_.' '[:lower:]--')"
echo "Publicado. Build: https://huggingface.co/spaces/${REPO}"
echo "URL do backend: https://${SUB}.hf.space"
