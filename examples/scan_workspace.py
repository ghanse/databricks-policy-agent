# Databricks notebook source
# MAGIC %md
# MAGIC # Scan a workspace for policy compliance
# MAGIC
# MAGIC This notebook runs an ad-hoc compliance scan against the current workspace using the
# MAGIC `policy_agent` library. It defines policies inline, scans the workspace, and shows the
# MAGIC findings.
# MAGIC
# MAGIC Scans are **read-only**. They fetches resource snapshots using the Databricks SDK,
# MAGIC then evaluate policies in memory. Data from scans can be converted to a DataFrame,
# MAGIC queried directly, and written to a table.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install the library
# MAGIC
# MAGIC We'll first install the policy agent library from GitHub.
# MAGIC
# MAGIC **NOTE:**
# MAGIC This step is only needed when running the notebook on a general-purpose cluster. The
# MAGIC provisioned app and jobs install the library by default.

# COMMAND ----------

# MAGIC %pip install 'git+https://github.com/ghanse/databricks-policy-agent'
# MAGIC %restart_python

# COMMAND ----------

# MAGIC %md
# MAGIC ## Define policies
# MAGIC
# MAGIC Policies are declared using a Python DSL (`allow` / `deny`, combined with `all_of`, `any_of`,
# MAGIC `leaf`). An `allow` policy is an allow-list: a resource is compliant only when its rule
# MAGIC matches. Each policy carries an `enforcement_level` of `advisory`, `soft`, or `hard` and
# MAGIC targets one `resource_type`. The examples below cover jobs, clusters, and SQL warehouses.
# MAGIC
# MAGIC **NOTE:**
# MAGIC The examples below cover jobs, clusters, and SQL warehouses. The same policies are also
# MAGIC available as YAML. See [`examples/`](https://github.com/ghanse/databricks-policy-agent/tree/main/examples).
# MAGIC Load policies from YAML using `load_policies_from_yaml`.

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
        remediation="Rename the job to start with 'prod_', 'stg_', or 'dev_'.",
    ),
    allow(
        name="clusters-must-auto-terminate",
        resource_type="cluster",
        rule=all_of(leaf("autotermination_minutes", "less_than", 60)),
        description="Interactive clusters must set an auto-termination window shorter than 60 minutes.",
        enforcement_level="soft",
        remediation="Set autotermination_minutes to a value less than 60 on the cluster.",
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
# MAGIC ## Run a scan
# MAGIC
# MAGIC `run_scan` fetches the resource types referenced by each policy, evaluates each applicable
# MAGIC policy against every workspace resource, and returns an immutable `ScanResult`.
# MAGIC
# MAGIC **NOTE:**
# MAGIC You must have *VIEW* access to scan workspace resources and evaluate their associated policies.
# MAGIC Scanning Unity Catalog securables requires *USE CATALOG* and *USE SCHEMA* permissions
# MAGIC on the securable's parent catalog and/or schema.

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
# MAGIC ## Review findings
# MAGIC
# MAGIC Each finding contains a combination of a policy and a resource. Build a table from the
# MAGIC findings to review, filter, or share the data.

# COMMAND ----------

findings = spark.createDataFrame(
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
    ],
)

display(findings)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Review Violations
# MAGIC
# MAGIC Violations are created when resources do not comply with defined policies.
# MAGIC Check the `result.violations` for a subset of findings that failed their policy.

# COMMAND ----------

violations = findings.where("not compliant")
display(violations)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next steps
# MAGIC
# MAGIC - For the complete policy syntax, Python DSL, and attribute reference, see
# MAGIC   [Documentation](https://github.com/ghanse/databricks-policy-agent/tree/main/docs).
# MAGIC - For example YAML policies for every resource type, see
# MAGIC   [Examples](https://github.com/ghanse/databricks-policy-agent/tree/main/examples).
# MAGIC - To gate deployments with Declarative Automation Bundles, see the `policy-agent enforce` CLI.
