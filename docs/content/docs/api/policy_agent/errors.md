---
sidebar_label: errors
title: policy_agent.errors
---

Exception hierarchy for the policy agent.

All library-raised errors derive from `PolicyAgentError` so callers can catch
the whole family with a single ``except`` while still distinguishing specific failures.

## PolicyAgentError Objects

```python
class PolicyAgentError(Exception)
```

Base class for every error raised by the policy agent.

## InvalidPolicyError Objects

```python
class InvalidPolicyError(PolicyAgentError)
```

Raised when a policy is structurally invalid or fails validation.

## UnknownConditionError Objects

```python
class UnknownConditionError(InvalidPolicyError)
```

Raised when a policy references an operator or attribute that is not registered.

## StorageError Objects

```python
class StorageError(PolicyAgentError)
```

Raised when a storage backend cannot read or write policy-agent state.

## AuthorizationError Objects

```python
class AuthorizationError(PolicyAgentError)
```

Raised when a caller lacks the role required for a workflow transition.

## WorkflowError Objects

```python
class WorkflowError(PolicyAgentError)
```

Raised when an approval transition is not legal from the current status.

## EnforcementError Objects

```python
class EnforcementError(PolicyAgentError)
```

Raised when a deployment bundle cannot be resolved or gated.

