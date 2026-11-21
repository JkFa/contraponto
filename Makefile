SHELL := /bin/bash
API := apps/api
WEB := apps/web
VENV := $(API)/.venv
PY := $(VENV)/bin/python
ENVFILE := $(wildcard .env)

.PHONY: setup dev mock test lint build format deploy-api e2e

setup:
	cd $(API) && uv venv --python 3.11 .venv && uv pip install --python .venv/bin/python -r requirements.txt -r requirements-dev.txt
	cd $(WEB) && npm ci
	@test -f .env || cp .env.example .env

dev:
	@set -a; [ -f .env ] && source .env; set +a; \
	trap 'kill 0' EXIT; \
	(cd $(API) && .venv/bin/uvicorn app.main:app --reload --port 8000) & \
	(cd $(WEB) && npm run dev) & \
	wait

mock:
	@set -a; [ -f .env ] && source .env; set +a; export MOCK_LLM=1 MOCK_TTS=1; \
	trap 'kill 0' EXIT; \
	(cd $(API) && .venv/bin/uvicorn app.main:app --reload --port 8000) & \
	(cd $(WEB) && npm run dev) & \
	wait

test:
	cd $(API) && MOCK_LLM=1 MOCK_TTS=1 .venv/bin/pytest -q
	cd $(WEB) && npm test -- --run

e2e:
	cd $(WEB) && npx playwright test

lint:
	cd $(API) && .venv/bin/ruff check . && .venv/bin/ruff format --check .
	cd $(WEB) && npm run lint && npx tsc --noEmit -p tsconfig.app.json

format:
	cd $(API) && .venv/bin/ruff format . && .venv/bin/ruff check --fix .

build:
	cd $(WEB) && npm run build

deploy-api:
	./scripts/deploy_space.sh
