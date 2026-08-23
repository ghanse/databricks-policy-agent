---
sidebar_label: conditions
title: policy_agent.policy.conditions
---

Condition evaluation and the registry of comparison operators.

Evaluating a condition tree is a pure walk over a resource snapshot (a flat mapping of
attribute names to values). Leaf comparisons delegate to named operators drawn from a fixed
registry, so no policy can execute arbitrary code — the entire operator vocabulary is the
functions in :data:`OPERATORS`.

#### evaluate\_condition

```python
def evaluate_condition(condition: Condition, snapshot: Snapshot) -> bool
```

Evaluate a condition tree against a single resource snapshot.

**Arguments**:

- `condition` - The condition tree to evaluate.
- `snapshot` - Flat mapping of resource attributes; dotted attribute paths index into
  nested mappings.
  

**Returns**:

  ``True`` when the condition holds for the snapshot, otherwise ``False``.
  

**Raises**:

- `UnknownConditionError` - If a leaf references an operator absent from the registry.

#### resolve\_attribute

```python
def resolve_attribute(snapshot: Snapshot, attribute: str) -> Any
```

Read an attribute from a snapshot, following dotted paths into nested mappings.

**Arguments**:

- `snapshot` - The resource snapshot.
- `attribute` - An attribute name or dotted path such as ``tags.environment``.
  

**Returns**:

  The attribute value, or ``None`` when any path segment is missing.

#### is\_registered\_operator

```python
def is_registered_operator(name: str) -> bool
```

Return whether ``name`` is a known comparison operator.

**Arguments**:

- `name` - Candidate operator name.
  

**Returns**:

  ``True`` if the operator exists in :data:`OPERATORS`.

#### registered\_operators

```python
def registered_operators() -> tuple[str, ...]
```

Return the sorted names of every registered comparison operator.

**Returns**:

  A tuple of operator names.

#### OPERATORS

The complete vocabulary of comparison operators, keyed by the name policies reference.

