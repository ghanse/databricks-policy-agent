---
sidebar_label: cli
title: policy_agent.cli
---

Command-line interface: ``policy-agent validate`` and ``policy-agent scan``.

``validate`` parses and validates policy YAML files offline. ``scan`` runs a compliance
scan against a workspace, either using policies from a file/directory or the approved
policies already in storage, and (unless ``--dry-run``) persists the outcome.

#### main

```python
def main(argv: Sequence[str] | None = None) -> int
```

Run the CLI.

**Arguments**:

- `argv` - Arguments to parse; defaults to ``sys.argv[1:]``.
  

**Returns**:

  Process exit code.

