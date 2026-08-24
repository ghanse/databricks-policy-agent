---
sidebar_label: bundle
title: policy_agent.enforce.bundle
---

Resolve a Databricks Asset Bundle to its fully-substituted configuration.

``databricks bundle validate --output json`` emits the resolved bundle (all variables and
target overrides applied). That JSON is the desired-state manifest the enforcement gate
evaluates before ``databricks bundle deploy`` runs — the DAB analogue of a Terraform plan.

#### load\_bundle\_config

```python
def load_bundle_config(source: str | Path,
                       target: str | None = None) -> dict[str, Any]
```

Load a resolved bundle configuration from a JSON file or by resolving a bundle dir.

**Arguments**:

- `source` - Either a path to a ``bundle validate --output json`` file, or a bundle
  directory to resolve.
- `target` - Bundle target to resolve when ``source`` is a directory.
  

**Returns**:

  The resolved bundle configuration.
  

**Raises**:

- `EnforcementError` - If the file cannot be parsed or the bundle cannot be resolved.

#### resolve\_bundle

```python
def resolve_bundle(bundle_dir: str | Path,
                   target: str | None = None) -> dict[str, Any]
```

Run ``databricks bundle validate --output json`` and return the parsed config.

**Arguments**:

- `bundle_dir` - Directory containing ``databricks.yml``.
- `target` - Bundle target to resolve (``-t``); the bundle default is used when ``None``.
  

**Returns**:

  The resolved bundle configuration.
  

**Raises**:

- ``0 - If the CLI is missing, validation fails, or output is not JSON.

