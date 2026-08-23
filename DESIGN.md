# Design

## Goals & principles

The Policy Agent enforces configuration compliance across Databricks workspace objects. The
design follows a few deliberate principles:

- **Pure, functional core.** The library is built from small, single-responsibility modules
  of pure functions over immutable dataclasses. State (the workspace, storage) is passed in
  at the edges; the policy model, evaluation, and the approval/remediation state machines
  hold no mutable state.
- **Declarative and safe by construction.** Policies are data — condition trees evaluated by
  a fixed operator registry. No policy can execute arbitrary code. Validation rejects
  unknown operators or attributes at author time.
- **Storage-agnostic.** One `SqlExecutor` interface backs both Unity Catalog Delta and
  Lakebase Postgres; the rest of the framework never branches on backend.
- **One model, three surfaces.** Ad-hoc code, the CLI, the jobs, and the app all converge on
  the same library functions, so behaviour is identical everywhere.

## Library architecture

```
policy/       model (enums, condition tree, Policy) · conditions (operator registry +
              evaluation) · validation · yaml_loader · python_dsl · serialization
scan/         resources (SDK → ResourceSnapshot) · registry (type → fetcher) ·
              evaluator (policy × snapshot → Finding) · engine (run_scan) · results
storage/      config (StorageConfig) · schema (tables + DDL/DML builders) · records
              (domain ↔ row) · backend (functions over SqlExecutor) · delta · lakebase
approval/     roles (RBAC) · workflow (transition state machine + ApprovalEvent)
remediation/  model (RemediationItem) · cycle (reconcile + manual transitions)
config · tagging · notify · schedule · cli · jobs (runner + entry points)
```

### Policy model

A `Policy` binds a `resource_type`, an `Effect` (allow/deny), and a condition tree (`rule`),
with an optional `match` selector. Condition nodes are frozen dataclasses — `Comparison`,
`AllOf`, `AnyOf`, `Negation`. `RESOURCE_ATTRIBUTES` in `policy.model` is the contract between
policy validation and scanning: it declares the attributes each resource type exposes, and
both the validator (rejecting unknown attributes) and the resource fetchers conform to it.

### Evaluation semantics

`evaluate_condition` walks the tree, delegating leaf comparisons to `OPERATORS`. The
evaluator maps a rule match to compliance by effect: allow-policies are compliant when the
rule matches; deny-policies are violations when it matches. A `match` selector that excludes
a resource yields no finding at all.

### Storage

Mutable entities (policies, remediations, schedules, role mappings) are upserted with
delete-then-insert, so neither Delta `MERGE` nor Postgres `ON CONFLICT` is needed and the SQL
builders stay dialect-portable. Append-only tables (scans, findings, approval events,
versions) are inserted directly. The Delta executor sends every value as a typed statement
parameter and reads results back as strings; the Lakebase executor uses native SQLAlchemy
types. Record readers coerce both to typed domain objects, so the two backends round-trip
through one code path. Configured tags are applied to created schemas/tables and stamped on
every row.

### Approval & remediation

Approval transitions are pure functions returning a new `Policy` plus an immutable
`ApprovalEvent`; role checks and legal-transition checks raise typed errors. Only approved
policies are run by scans. The remediation cycle keys items by
`(policy, resource type, resource id)`; `reconcile` opens items for new violations and
auto-resolves items whose violation has cleared.

## App

The FastAPI backend is a thin HTTP layer over the library: dependencies expose process-wide
state (config, executor, workspace client) built once at startup; routes call library
functions directly; domain exceptions map to HTTP status codes. Authorization resolves a
caller's roles from their workspace-group membership against stored role mappings, with a
bootstrap that grants admin when no mappings exist yet. The React SPA is a small tabbed
client served as static files by the same process.

## Deployment

A single Declarative Asset Bundle provisions the app, the two scan jobs, and the storage
bootstrap (SQL warehouse + UC schema). Jobs are Python wheel tasks that read `POLICY_AGENT_*`
configuration from their cluster environment — identical to the app's configuration — so a
single `config_from_env` drives every runtime. Deployment requires a workspace-admin service
principal.

## Testing

Unit tests cover the pure core exhaustively (parsing, evaluation, storage round-trips via an
in-memory executor, workflow and remediation transitions, config, CLI, notifications) and
the app API via FastAPI's TestClient with dependency overrides. Integration tests use the
Databricks Labs pytester fixtures to create real jobs and schemas, scan them, and round-trip
storage against a live workspace.
