---
sidebar_label: tagging
title: policy_agent.tagging
---

Helpers for the tags stamped onto every object the policy agent creates.

A managed marker tag is always present so operators can find and audit policy-agent-owned
objects; user-supplied tags are merged on top.

#### managed\_tags

```python
def managed_tags(extra_tags: dict[str, str] | None = None) -> dict[str, str]
```

Return the managed marker tag merged with any extra tags.

**Arguments**:

- `extra_tags` - Additional tags to apply; these override the marker on key collision.
  

**Returns**:

  A tag mapping that always includes the managed marker.

#### parse\_tags

```python
def parse_tags(raw: str) -> dict[str, str]
```

Parse tags from a string in either JSON object or ``key=value,key=value`` form.

**Arguments**:

- `raw` - The raw tag string; an empty string yields no tags.
  

**Returns**:

  The parsed tag mapping.

