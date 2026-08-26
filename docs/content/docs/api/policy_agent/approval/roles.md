---
sidebar_label: roles
title: policy_agent.approval.roles
---

Role model and role resolution for the approval workflow.

Roles are granted to workspace groups; a caller's effective roles are the union of the roles
mapped to every group they belong to. The permission predicates below are the single source
of truth for which role a workflow transition requires.

## Role Objects

```python
class Role(str, Enum)
```

A privilege level in the policy approval workflow.

#### resolve\_roles

```python
def resolve_roles(group_names: Iterable[str],
                  role_mappings: Mapping[str, Iterable[Role]]) -> set[Role]
```

Resolves the effective roles for a caller from their group memberships.

**Arguments**:

- `group_names` - The workspace groups the caller belongs to.
- `role_mappings` - Mapping from group name to the roles granted to that group.
  

**Returns**:

  The union of roles granted by the caller's groups.

#### can\_author

```python
def can_author(roles: Collection[Role]) -> bool
```

Whether the roles permit drafting and submitting policies.

**Arguments**:

- `roles` - The caller's effective roles.
  

**Returns**:

  ``True`` if authoring is permitted.

#### can\_approve

```python
def can_approve(roles: Collection[Role]) -> bool
```

Whether the roles permit approving or rejecting policies.

**Arguments**:

- `roles` - The caller's effective roles.
  

**Returns**:

  ``True`` if approval is permitted.

#### can\_run\_scans

```python
def can_run_scans(roles: Collection[Role]) -> bool
```

Whether the roles permit running scans.

**Arguments**:

- `roles` - The caller's effective roles.
  

**Returns**:

  ``True`` if running scans is permitted.

#### can\_administer

```python
def can_administer(roles: Collection[Role]) -> bool
```

Whether the roles permit administrative actions such as archiving.

**Arguments**:

- `roles` - The caller's effective roles.
  

**Returns**:

  ``True`` if administration is permitted.

