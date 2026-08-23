# Databricks Policy Agent

A policy compliance framework for Databricks workspace objects. Declare **allow**/**deny**
policies over Jobs, Clusters, SQL Warehouses, Apps, and Model Serving Endpoints; scan the
workspace for compliance; track violations through a remediation cycle; and gate policy
changes behind a draft → review → approve workflow.

It ships as three coordinated pieces:

- **`policy_agent` library** — the pure, functional core: policy model, scan engine,
  configurable storage (Unity Catalog Delta *or* Lakebase Postgres), and the approval and
  remediation state machines.
- **Databricks App** — a FastAPI JSON API and a React single-page app for authoring
  policies, running scans, reviewing findings, and approving policy changes.
- **Provisioned jobs** — on-demand and scheduled scans that persist results and reconcile
  the remediation cycle.

## Layout

```
src/policy_agent/        library (policy/ scan/ storage/ approval/ remediation/ jobs/)
app/                     Databricks App: FastAPI backend + React SPA (src/policy_agent_app)
docs/                    Docusaurus site; API reference generated from docstrings
examples/                sample OPA-style policy YAML, one file per resource type
databricks.yml           single Declarative Asset Bundle (app + jobs + storage)
tests/                   unit tests and pytester-based integration tests
```

## Develop

```bash
make dev        # uv sync --all-extras (library)
make fmt        # ruff format + fix
make lint       # ruff format --check, ruff check, mypy
make test       # unit tests
make coverage   # unit tests with coverage
```

App and docs are separate projects:

```bash
cd app && uv sync --group dev && uv run pytest tests          # backend
cd app/src/policy_agent_app/ui && npm install && npm run build # SPA
cd docs && npm install && uv run --project .. pydoc-markdown && npm run build  # docs
```

## Author & validate policies

```bash
uv run policy-agent validate examples/
uv run policy-agent scan --profile <profile> --policies examples/ --dry-run
```

See [`docs/`](docs/) for the full guide: policy syntax, the Python DSL, scanning, storage,
the approval workflow, remediation, and deployment. Architecture is in
[`DESIGN.md`](DESIGN.md).

## Deploy

```bash
cd app && uv run python scripts/build_app.py && cd ..   # build SPA + wheel + app tree
cp target.dev.yml.example target.dev.yml                # configure your workspace
databricks bundle deploy -t dev -p <profile>            # as a workspace-admin service principal
```
