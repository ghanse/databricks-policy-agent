---
sidebar_label: conditions
title: policy_agent.policy.conditions
---

Condition evaluation and the registry of comparison operators.

Evaluating a condition tree is a pure walk over a resource snapshot (a flat mapping of
attribute names to values). Leaf comparisons delegate to named operators drawn from a fixed
registry, so no policy can execute arbitrary code — the entire operator vocabulary is the
functions in `OPERATORS`.

#### evaluate\_condition

```python
def evaluate_condition(condition: Condition, snapshot: Snapshot) -> bool
```

Evaluates a condition tree against a single resource snapshot.

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

Reads an attribute from a snapshot, following dotted paths into nested mappings.

At each level the longest leading run of segments that is a literal key is matched before
descending, so a dotted path resolves a key that itself contains dots — for example
``properties.delta.enableChangeDataFeed`` finds the ``delta.enableChangeDataFeed`` key of a
``properties`` mapping, and ``tags.environment`` still finds the ``environment`` key of
``tags``.

The match is greedy and does not backtrack, which is unambiguous because each mapping a
snapshot exposes is either nested simple keys (``tags``) or a flat map of literal dotted keys
(``properties``), never both at one level. A future attribute that nested maps under a
dotted-key level would need this resolver revisited.

**Arguments**:

- `snapshot` - The resource snapshot.
- `attribute` - An attribute name or dotted path such as ``tags.environment``.
  

**Returns**:

  The attribute value, or ``None`` when the path does not resolve.

#### is\_registered\_operator

```python
def is_registered_operator(name: str) -> bool
```

Returns whether ``name`` is a known comparison operator.

**Arguments**:

- `name` - Candidate operator name.
  

**Returns**:

  ``True`` if the operator exists in `OPERATORS`.

#### registered\_operators

```python
def registered_operators() -> tuple[str, ...]
```

Returns the sorted names of every registered comparison operator.

**Returns**:

  A tuple of operator names.

#### OPERATORS

The complete vocabulary of comparison operators, keyed by the name policies reference.

