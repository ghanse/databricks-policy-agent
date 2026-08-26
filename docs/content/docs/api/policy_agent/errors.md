---
sidebar_label: errors
title: policy_agent.errors
---

Exception hierarchy for the policy agent.

All library-raised exceptions derive from `PolicyAgentException` so callers can catch the whole
family with a single ``except`` while still distinguishing specific failures.

## PolicyAgentException Objects

```python
class PolicyAgentException(Exception)
```

Base class for every exception raised by the policy agent.

## InvalidPolicyError Objects

```python
class InvalidPolicyError(PolicyAgentException)
```

Raised when a policy is structurally invalid or fails validation.

## UnknownConditionError Objects

```python
class UnknownConditionError(InvalidPolicyError)
```

Raised when a policy references an operator or attribute that is not registered.

## UnsupportedResourceException Objects

```python
class UnsupportedResourceException(PolicyAgentException)
```

Raised when a resource type is not supported by the requested operation.

## StorageError Objects

```python
class StorageError(PolicyAgentException)
```

Raised when a storage backend cannot read or write policy-agent state.

## AuthorizationError Objects

```python
class AuthorizationError(PolicyAgentException)
```

Raised when a caller lacks the role required for a workflow transition.

## WorkflowError Objects

```python
class WorkflowError(PolicyAgentException)
```

Raised when an approval transition is not legal from the current status.

## EnforcementError Objects

```python
class EnforcementError(PolicyAgentException)
```

Raised when a deployment bundle cannot be resolved or gated.

