# Databricks notebook source
# MAGIC %md
# MAGIC # Scan a workspace for policy compliance
# MAGIC
# MAGIC This notebook runs an ad-hoc compliance scan against the current workspace with the
# MAGIC `policy_agent` library. It defines a few policies inline, scans the workspace, and shows
# MAGIC the findings.
# MAGIC
# MAGIC The scan is **read-only**: it fetches resource snapshots through the Databricks SDK and
# MAGIC evaluates the policies in memory. Nothing is written to storage, so no catalog, schema,
# MAGIC or SQL warehouse configuration is required. Persisting results is shown as an optional
# MAGIC step at the end.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install the library
# MAGIC
# MAGIC In the provisioned app and jobs the wheel is already installed, so this step is only
# MAGIC needed when running the notebook on a general-purpose cluster.

# COMMAND ----------

# MAGIC %pip install databricks-policy-agent
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Define policies
# MAGIC
# MAGIC Policies are declared with the Python DSL (`allow` / `deny`, combined with `all_of`,
# MAGIC `any_of`, `leaf`). An `allow` policy is an allow-list: a resource is compliant only when
# MAGIC its rule matches. Each policy targets one `resource_type` and carries an
# MAGIC `enforcement_level` of `advisory`, `soft`, or `hard`.
# MAGIC
# MAGIC The examples below cover jobs, clusters, and SQL warehouses. The same policies are also
# MAGIC available as YAML under [`examples/`](https://github.com/ghanse/databricks-policy-agent/tree/main/examples);
# MAGIC load those with `load_policies_from_yaml` instead of the DSL if you prefer.

# COMMAND ----------

from policy_agent import all_of, allow, leaf

policies = [
    allow(
        name="jobs-must-be-tagged",
        resource_type="job",
        rule=all_of(leaf("tags", "not_empty")),
        description="Every job must carry at least one tag for cost attribution and ownership.",
        enforcement_level="soft",
        remediation="Add one or more tags to the job.",
    ),
    allow(
        name="jobs-naming-convention",
        resource_type="job",
        rule=all_of(leaf("name", "matches_regex", r"^(prod|stg|dev)_[a-z0-9_]+$")),
        description="Job names must be prefixed with an environment (prod_, stg_, or dev_).",
        enforcement_level="advisory",
        remediation="Rename the job to start with prod_, stg_, or dev_.",
    ),
    allow(
        name="clusters-must-auto-terminate",
        resource_type="cluster",
        rule=all_of(leaf("autotermination_minutes", "greater_than", 0)),
        description="Interactive clusters must set an auto-termination window.",
        enforcement_level="soft",
        remediation="Set autotermination_minutes to a nonzero value on the cluster.",
    ),
    allow(
        name="warehouses-should-be-serverless",
        resource_type="sql_warehouse",
        rule=all_of(leaf("enable_serverless_compute", "equals", True)),
        description="SQL warehouses should run on serverless compute.",
        enforcement_level="advisory",
        remediation="Enable serverless compute on the SQL warehouse.",
    ),
]

for policy in policies:
    print(f"{policy.name}: {policy.resource_type.value} / {policy.enforcement_level.value}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run the scan
# MAGIC
# MAGIC `run_scan` fetches only the resource types referenced by the policies (here jobs,
# MAGIC clusters, and SQL warehouses), evaluates every applicable policy against every resource,
# MAGIC and returns an immutable `ScanResult`. Pass `resource_types=[...]` to restrict the scan
# MAGIC further.

# COMMAND ----------

from databricks.sdk import WorkspaceClient

from policy_agent import run_scan

result = run_scan(WorkspaceClient(), policies)

summary = result.summary()
print(f"scan {result.scan_id}")
print(f"  evaluated:   {summary.evaluated}")
print(f"  violations:  {summary.violations}")
print(f"  compliance:  {summary.compliance_rate:.1%}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Inspect the findings
# MAGIC
# MAGIC Each finding is one (policy, resource) evaluation. Build a table from the findings to
# MAGIC review them, filter, or export.

# COMMAND ----------

import pandas as pd

findings = pd.DataFrame(
    [
        {
            "policy_name": finding.policy_name,
            "resource_type": finding.resource_type.value,
            "resource_id": finding.resource_id,
            "resource_name": finding.resource_name,
            "compliant": finding.compliant,
            "enforcement_level": finding.enforcement_level.value,
            "message": finding.message,
            "remediation": finding.remediation,
            "owner": finding.owner,
        }
        for finding in result.findings
    ]
)

display(findings)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Violations only
# MAGIC
# MAGIC `result.violations` is the subset of findings that failed their policy.

# COMMAND ----------

for finding in result.violations:
    print(
        f"[{finding.enforcement_level.value}] {finding.policy_name} "
        f"-> {finding.resource_name}: {finding.remediation}"
    )

if not result.violations:
    print("No violations found.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Persisting results (optional)
# MAGIC
# MAGIC The scan above evaluates policies without writing anything. To persist scan results and
# MAGIC reconcile the remediation cycle — as the provisioned jobs do — use `run_policy_scan`
# MAGIC with a configured storage backend. Configuration is read from `POLICY_AGENT_*`
# MAGIC environment variables:
# MAGIC
# MAGIC | Variable | Purpose |
# MAGIC | --- | --- |
# MAGIC | `POLICY_AGENT_STORAGE_BACKEND` | `unity_catalog` (default) or `lakebase` |
# MAGIC | `POLICY_AGENT_CATALOG` / `POLICY_AGENT_SCHEMA` | Where state tables live |
# MAGIC | `POLICY_AGENT_WAREHOUSE_ID` | SQL warehouse for the Unity Catalog backend |
# MAGIC | `POLICY_AGENT_LAKEBASE_URL` | SQLAlchemy URL for the Lakebase backend |
# MAGIC
# MAGIC The cell below is commented out because it requires that configuration.

# COMMAND ----------

# from policy_agent import config_from_env, create_executor
# from policy_agent.jobs.runner import run_policy_scan
#
# config = config_from_env()
# workspace_client = WorkspaceClient()
# executor = create_executor(config, workspace_client)
# result = run_policy_scan(workspace_client, executor, config, policies, triggered_by="notebook")
# print(result.summary())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next steps
# MAGIC
# MAGIC - Policy syntax, the Python DSL, and the full attribute reference are in the
# MAGIC   [docs](https://github.com/ghanse/databricks-policy-agent/tree/main/docs).
# MAGIC - Ready-made example policies for every resource type are under
# MAGIC   [`examples/`](https://github.com/ghanse/databricks-policy-agent/tree/main/examples).
# MAGIC - To gate a Databricks Asset Bundle before deployment, see the `policy-agent enforce` CLI.
