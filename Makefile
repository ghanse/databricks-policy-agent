.PHONY: dev fmt lint test coverage build integration \
        lock-dependencies lock-docs-dependencies lock-app-dependencies \
        docs docs-install docs-build docs-serve \
        app-install app-build app-lint app-test clean

UV_RUN := uv run --exact --all-extras
UV_TEST := $(UV_RUN) pytest -n 10 --timeout 60 --durations 20

# After ``uv lock`` resolves through the internal PyPI proxy, the lock is tainted with
# proxy URLs. This rewrites the registry index and every per-package download URL back to
# the public PyPI hosts, and drops the proxy-only ``size`` field, so the committed lock is
# identical for contributors inside Databricks (proxy) and outside (public PyPI).
SANITIZE_LOCK := perl -pi -e 's|registry = "https://[^"]*"|registry = "https://pypi.org/simple"|g; s|url = "https://[^/"]+/packages/|url = "https://files.pythonhosted.org/packages/|g; s|, size = \d+||g'

# npm lockfiles are likewise tainted with the internal npm proxy host after ``npm install``
# runs through it. Swap the proxy host back to the public npm registry; the paths and the
# integrity hashes are identical, so the committed lock installs cleanly on public runners.
SANITIZE_NPM_LOCK := perl -pi -e 's|https://npm-proxy\.cloud\.databricks\.com/|https://registry.npmjs.org/|g'

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

# Regenerate the library lock and sanitize proxy URLs out of it.
lock-dependencies:
	uv lock
	$(SANITIZE_LOCK) uv.lock

# Regenerate the docs npm lock and sanitize the proxy host out of it.
lock-docs-dependencies:
	cd docs && npm install
	$(SANITIZE_NPM_LOCK) docs/package-lock.json

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

# Regenerate the app locks (Python + UI npm) and sanitize proxy URLs out of both.
lock-app-dependencies:
	cd app && uv lock
	$(SANITIZE_LOCK) app/uv.lock
	cd app/src/policy_agent_app/ui && npm install
	$(SANITIZE_NPM_LOCK) app/src/policy_agent_app/ui/package-lock.json

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
