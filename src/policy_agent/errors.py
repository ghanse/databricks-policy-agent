"""Exception hierarchy for the policy agent.

All library-raised exceptions derive from `PolicyAgentException` so callers can catch the whole
family with a single ``except`` while still distinguishing specific failures.
"""


class PolicyAgentException(Exception):
    """Base class for every exception raised by the policy agent."""


# Backwards-compatible alias for the historical base-class name.
PolicyAgentError = PolicyAgentException


class InvalidPolicyError(PolicyAgentException):
    """Raised when a policy is structurally invalid or fails validation."""


class UnknownConditionError(InvalidPolicyError):
    """Raised when a policy references an operator or attribute that is not registered."""


class UnsupportedResourceException(PolicyAgentException):
    """Raised when a resource type is not supported by the requested operation."""


class StorageError(PolicyAgentException):
    """Raised when a storage backend cannot read or write policy-agent state."""


class AuthorizationError(PolicyAgentException):
    """Raised when a caller lacks the role required for a workflow transition."""


class WorkflowError(PolicyAgentException):
    """Raised when an approval transition is not legal from the current status."""


class EnforcementError(PolicyAgentException):
    """Raised when a deployment bundle cannot be resolved or gated."""
