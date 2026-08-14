---
sidebar_position: 9
---

# Deployment

Everything deploys through a single Declarative Asset Bundle (`databricks.yml`): the
Databricks App, the on-demand and scheduled scan jobs, and the storage bootstrap (a SQL
warehouse and the Unity Catalog schema). Deploy as a **workspace-admin service principal**.

## Steps

```bash
# 1. Build the SPA, the library wheel, and assemble the deployable app tree.
cd app && uv run python scripts/build_app.py && cd ..

# 2. Configure the target for your workspace (never committed).
cp target.dev.yml.example target.dev.yml   # edit catalog, tags, service principal, node type

# 3. Deploy.
databricks bundle deploy -t dev -p <profile>
```

## Configuration

The app and jobs read these environment variables (set by the bundle):

| Variable | Purpose |
| --- | --- |
| `POLICY_AGENT_STORAGE_BACKEND` | `uc` or `lakebase` |
| `POLICY_AGENT_CATALOG` | Unity Catalog catalog (UC backend) |
| `POLICY_AGENT_SCHEMA` | schema holding the tables |
| `POLICY_AGENT_WAREHOUSE_ID` | SQL warehouse id (UC backend) |
| `POLICY_AGENT_LAKEBASE_URL` | SQLAlchemy URL (Lakebase backend) |
| `POLICY_AGENT_TAGS` | tags stamped on created objects (`key=value,key=value`) |
| `POLICY_AGENT_NOTIFICATION_EMAILS` | comma-separated recipients |
| `POLICY_AGENT_NOTIFICATION_WEBHOOK` | webhook posted with violation summaries |

## Scheduling

The scheduled scan job runs on the cron in `scan_cron` (default daily at 06:00) and scans
every approved policy. Adjust the cadence per target in `databricks.yml` or the target file.
