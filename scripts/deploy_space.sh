#!/usr/bin/env bash
# Publishes apps/api to a Hugging Face Space (Docker). Idempotent.
# Requires: `pip install -U huggingface_hub` (CLI `hf`) and `hf auth login` with a write token.
# Usage: HF_USER=<your-hf-username> ./scripts/deploy_space.sh   (HF_USER is detected if omitted)
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
if ! hf auth whoami >/dev/null 2>&1; then
  echo "Faça login primeiro: hf auth login (token com permissão de escrita)" >&2
  exit 1
fi
HF_USER="${HF_USER:-$(hf auth whoami | head -n1 | sed -E 's/^(user: *)?//; s/ .*//')}"
REPO="${HF_USER}/${SPACE_NAME}"
echo "Space: ${REPO}"

hf repo create "${SPACE_NAME}" --repo-type space --space-sdk docker --exist-ok >/dev/null 2>&1 \
  || hf repo create "${SPACE_NAME}" --type space --space-sdk docker >/dev/null 2>&1 \
  || echo "(o Space já existe ou foi criado antes)"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
git clone --quiet "https://huggingface.co/spaces/${REPO}" "$WORK/space"
rsync -a --delete --exclude '.git' --exclude '__pycache__' --exclude '.venv' --exclude '.data' \
  --exclude '.pytest_cache' --exclude '.ruff_cache' "$ROOT/apps/api/" "$WORK/space/"
cd "$WORK/space"
git add -A
if git diff --cached --quiet; then
  echo "Nada mudou; Space já está atualizado."
else
  git commit --quiet -m "deploy $(cd "$ROOT" && git rev-parse --short HEAD)"
  git push --quiet
  echo "Publicado. Acompanhe o build em https://huggingface.co/spaces/${REPO}"
fi
echo "URL do backend: https://${HF_USER,,}-${SPACE_NAME}.hf.space"
