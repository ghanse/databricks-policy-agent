"""Exception hierarchy for the policy agent.

All library-raised errors derive from :class:`PolicyAgentError` so callers can catch
the whole family with a single ``except`` while still distinguishing specific failures.
"""


class PolicyAgentError(Exception):
    """Base class for every error raised by the policy agent."""


class InvalidPolicyError(PolicyAgentError):
    """Raised when a policy is structurally invalid or fails validation."""


class UnknownConditionError(InvalidPolicyError):
    """Raised when a policy references an operator or attribute that is not registered."""


class StorageError(PolicyAgentError):
    """Raised when a storage backend cannot read or write policy-agent state."""


class AuthorizationError(PolicyAgentError):
    """Raised when a caller lacks the role required for a workflow transition."""


class WorkflowError(PolicyAgentError):
    """Raised when an approval transition is not legal from the current status."""


class EnforcementError(PolicyAgentError):
    """Raised when a deployment bundle cannot be resolved or gated."""
