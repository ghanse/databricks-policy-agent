.PHONY: dev fmt lint test coverage build integration \
        docs docs-install docs-build docs-serve \
        app-install app-build app-lint app-test clean

UV_RUN := uv run --exact --all-extras
UV_TEST := $(UV_RUN) pytest -n 10 --timeout 60 --durations 20

# Library:
dev:
	uv sync --all-extras

fmt:
	uv run ruff format src tests
	uv run ruff check --fix src tests
	uv run mypy src

lint:
	uv run ruff format --check src tests
	uv run ruff check src tests
	uv run mypy src

test:
	uv run pytest tests/unit

coverage:
	uv run pytest tests/unit --cov=policy_agent --cov-report=term-missing --cov-report=xml

build:
	uv build --wheel

integration:
	uv run pytest tests/integration -m integration

# Documentation:
docs-install:
	cd docs && npm ci

docs-build:
	cd docs && uv run --project .. pydoc-markdown && npm run build

docs: docs-install docs-build

docs-serve:
	cd docs && npm run start

# App:
app-install:
	cd app && uv sync --group dev
	cd app/src/policy_agent_app/ui && npm ci

app-build:
	cd app && uv run python scripts/build_app.py

app-lint:
	cd app && uv run ruff format --check src tests
	cd app && uv run ruff check src tests
	cd app && uv run mypy src

app-test:
	cd app && uv run pytest tests

clean:
	rm -rf dist build .mypy_cache .ruff_cache .pytest_cache app/.build docs/build docs/.docusaurus
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
