---
name: author
description: "Author and validate Databricks Policy Agent compliance policies. Use when writing allow/deny policies over Databricks workspace objects (jobs, clusters, SQL warehouses, apps, serving endpoints, Unity Catalog objects, pipelines, and more), choosing resource attributes or operators, using the Python DSL, or validating policy YAML with the `policy-agent validate` CLI or `policy_agent` library. See also policy-agent:scan and policy-agent:enforce."
---

# Authoring & validating policies

The [Policy Agent](https://github.com/ghanse/databricks-policy-agent) declares **allow**/**deny**
compliance policies over Databricks workspace objects. A policy binds one `resource_type`, an
`effect`, and a condition `rule` (a tree over the resource's attributes), with an optional `match`
selector. Policies are declarative data — the only executable part is a fixed operator registry, so
a policy can never run arbitrary code, and validation rejects unknown attributes or operators at
author time.

Once authored, run policies with **policy-agent:scan** (live workspace) or **policy-agent:enforce**
(bundle deploy gate).

## A policy at a glance

```yaml
policy: production-jobs-need-failure-alerts
description: Production jobs must configure on-failure email notifications.
resource_type: job
effect: allow                     # allow = compliant only when the rule matches
enforcement_level: hard           # advisory | soft | hard
match:                            # optional selector: which resources this applies to
  all:
    - { attribute: name, operator: matches_regex, value: "^prod_.+$" }
rule:                             # the compliance condition
  all:
    - { attribute: has_email_notifications, operator: equals, value: true }
remediation: Add an on-failure email notification to the job.
```

Ready-made policies for every resource type live in
[`examples/`](https://github.com/ghanse/databricks-policy-agent/tree/main/examples), one YAML file
per type — copy from there.

## Policy schema

| Key | Required | Notes |
| --- | --- | --- |
| `policy` (or `name`) | yes | Unique identifier. |
| `resource_type` | yes | One of the resource types below. |
| `effect` | yes | `allow` or `deny`. |
| `rule` | yes | The compliance condition tree. |
| `description` | no | Free-text intent. |
| `enforcement_level` | no | `advisory` (default), `soft`, or `hard`. |
| `match` | no | Selector limiting which resources the policy applies to. |
| `remediation` | no | Guidance shown for a violation. |
| `status` | no | `draft` (default), `in_review`, `approved`, `rejected`, `archived`. |
| `version` | no | Integer, defaults to `1`. |

A YAML file may hold one policy mapping, a list of them, or several documents separated by `---`.
Every loaded policy is validated immediately, so a bad policy fails at load time.

### Effect semantics

- **`allow`** is an allow-list: a resource is **compliant only when `rule` matches**.
- **`deny`** is a deny-list: a resource is a **violation when `rule` matches**.
- A `match` selector that excludes a resource produces **no finding** for it — use it to scope a
  policy to a subset (e.g. only `prod_` jobs).

### Enforcement levels

Ordered least to most strict: `advisory` < `soft` < `hard`. `advisory` only reports; `soft` blocks
the deploy gate but can be overridden with a recorded reason; `hard` blocks and cannot be
overridden. See **policy-agent:enforce**.

## Condition trees

A condition is one of four node shapes:

```yaml
{ all: [ <condition>, ... ] }        # conjunction — true when every child is true
{ any: [ <condition>, ... ] }        # disjunction — true when at least one child is true
{ not: <condition> }                 # negation
{ attribute: <name>, operator: <op>, value: <expected> }   # leaf comparison
```

Leaves read an attribute off the resource and compare it with an operator. Dotted paths index into
nested mappings, e.g. `attribute: tags.environment`.

### Operators

| Operator | Compares | `value` |
| --- | --- | --- |
| `equals` / `not_equals` | equality | any |
| `matches_regex` | regex search over the string form | pattern string |
| `in` / `not_in` | membership in a list | list |
| `exists` / `absent` | attribute is / isn't present (non-null) | ignored |
| `less_than` / `greater_than` | numeric comparison (non-bool numbers) | number |
| `contains` | membership *within* the attribute value | element |
| `has_tag` / `missing_tag` | tag key present / absent in a tag mapping | tag key |
| `not_empty` | attribute has length > 0 | ignored |
| `owner_is_service_principal` | owner_type is a service principal | ignored |
| `ttl_within` | `0 < attribute <= value` seconds | max seconds |

## Resource types and their attributes

Validation rejects any attribute a resource type does not expose. Every type below carries the
identity attributes `id` and `name`. Types marked *owned* add `owner`, `owner_type`; *taggable* add
`tags`; *timestamped* add `created_time`.

| Resource type | Extra attributes (beyond id/name/owner/tags/created_time) |
| --- | --- |
| `job` | `schedule_pause_status`, `max_concurrent_runs`, `timeout_seconds`, `run_as_type`, `has_email_notifications`, `has_retry_policy`, `uses_serverless_compute`, `format` |
| `cluster` | `cluster_source`, `autotermination_minutes`, `spark_version`, `node_type_id`, `num_workers`, `data_security_mode`, `single_user_name` |
| `sql_warehouse` | `warehouse_type`, `cluster_size`, `auto_stop_minutes`, `enable_serverless_compute`, `min_num_clusters`, `max_num_clusters` |
| `app` | `app_status`, `compute_status`, `active_deployment_mode` |
| `serving_endpoint` | `endpoint_state`, `endpoint_type`, `budget_policy_id`, `route_optimized` |
| `pipeline` | `catalog`, `target`, `schema`, `channel`, `edition`, `continuous`, `photon`, `serverless`, `development` |
| `catalog` | `comment`, `catalog_type`, `isolation_mode`, `storage_root` |
| `schema` | `comment`, `catalog_name` |
| `volume` | `comment`, `catalog_name`, `schema_name`, `volume_type` |
| `table` | `comment`, `catalog_name`, `schema_name`, `table_type`, `data_source_format`, `storage_location`, `properties`, `enable_predictive_optimization`, `pipeline_id`, `view_definition` |
| `external_location` | `comment`, `url`, `credential_name`, `read_only`, `isolation_mode` |

Types with narrower attribute sets:

- `registered_model` *(owned, timestamped — no tags)*: `comment`, `catalog_name`, `schema_name`.
- `column` *(taggable — no owner/timestamp)*: `table_name`, `catalog_name`, `schema_name`,
  `data_type`, `type_text`, `type_precision`, `type_scale`, `position`, `nullable`, `comment`,
  `partition_index`, `has_mask`.
- `genie_space` *(taggable — no owner/timestamp)*: `warehouse_id`, `description`, `has_description`.
- `sql_alert` *(owned, timestamped — no tags)*: `warehouse_id`, `run_as_user_name`, `state`,
  `lifecycle_state`, `comparison_operator`, `empty_result_state`, `has_schedule`.
- `quality_monitor` *(id/name only)*: `table_name`, `output_schema_name`, `output_schema_id`,
  `monitor_type`, `has_schedule`.
- `notebook` *(id/name only)*: `path`, `language`.
- `workspace_file` *(timestamped)*: `path`, `size`.
- `secret_scope` *(id/name only)*: `backend_type`.

Only *taggable* types accept a `tags` (or `has_tag`/`missing_tag`) condition; a tag policy on any
other type is rejected at author time.

## The Python DSL

For code that builds policies programmatically, the DSL wraps the model types and coerces string
enum values:

```python
from policy_agent import allow, deny, all_of, any_of, not_, leaf, ResourceType

policy = allow(
    name="clusters-must-autoterminate",
    resource_type=ResourceType.CLUSTER,       # or just "cluster"
    enforcement_level="soft",
    rule=all_of(
        leaf("autotermination_minutes", "greater_than", 0),
        leaf("autotermination_minutes", "less_than", 120),
    ),
    remediation="Set autotermination to under 120 minutes.",
)
```

Constructors: `allow(...)`, `deny(...)`, and `policy(..., effect=...)` build policies; `all_of`,
`any_of`, `not_`, and `leaf` build the condition tree. Policies default to
`enforcement_level="advisory"` and `status="draft"`.

## Validate

From the CLI — offline, no workspace connection:

```bash
uv run policy-agent validate examples/          # a directory of .yml/.yaml files
uv run policy-agent validate my_policy.yaml      # a single file
```

`validate` reports `OK`/`ERR` per file and exits non-zero if any file fails.

From Python — `load_policies_from_yaml` loads and validates in one call, and `validate_policy`
checks an in-memory policy (both raise `PolicyAgentError` on the first problem):

```python
from policy_agent import load_policies_from_yaml, validate_policy

# Loading from a file (or a YAML string) validates every policy and raises on failure.
policies = load_policies_from_yaml("examples/jobs.yaml")

# Validate a policy built in code, e.g. from the DSL above.
validate_policy(policy)
```
