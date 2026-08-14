.PHONY: dev fmt lint test coverage clean app-build docs docs-serve

dev:
	uv sync --all-extras

fmt:
	uv run ruff format src tests
	uv run ruff check --fix src tests

lint:
	uv run ruff format --check src tests
	uv run ruff check src tests
	uv run mypy src

test:
	uv run pytest tests/unit

coverage:
	uv run pytest tests/unit --cov=policy_agent --cov-report=term-missing

integration:
	uv run pytest tests/integration -m integration

app-build:
	cd app && uv run python scripts/build_app.py

docs:
	cd docs && uv run --project .. pydoc-markdown && npm run build

docs-serve:
	cd docs && npm run start

clean:
	rm -rf dist build .mypy_cache .ruff_cache .pytest_cache app/.build docs/build docs/.docusaurus
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
