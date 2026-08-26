"""Loads and dump policies in the OPA-style YAML authoring format.

A YAML source may hold a single policy mapping, a top-level list of policies, or several
documents separated by ``---``. Loaded policies are validated before being returned so a
malformed policy fails fast at load time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from policy_agent.errors import InvalidPolicyError
from policy_agent.policy.model import Policy
from policy_agent.policy.serialization import policy_from_dict, policy_to_dict
from policy_agent.policy.validation import validate_policy


def load_policies_from_yaml(source: str | Path) -> list[Policy]:
    """Loads and validate every policy from a YAML string or file path.

    Args:
        source: Either YAML text or a path to a ``.yml``/``.yaml`` file.

    Returns:
        The validated policies, in document order.

    Raises:
        InvalidPolicyError: If the YAML is malformed or any policy fails validation.
    """
    text = _read_source(source)
    policies = [
        policy_from_dict(mapping) for document in _safe_load_documents(text) for mapping in document
    ]
    for policy in policies:
        validate_policy(policy)
    return policies


def dump_policies_to_yaml(policies: list[Policy]) -> str:
    """Serialises policies to a single multi-document YAML string.

    Args:
        policies: The policies to serialise.

    Returns:
        YAML text with one document per policy, in the given order.
    """
    documents = [policy_to_dict(policy) for policy in policies]
    return yaml.safe_dump_all(documents, sort_keys=False)


def _read_source(source: str | Path) -> str:
    if isinstance(source, Path):
        return source.read_text(encoding="utf-8")
    candidate = Path(source)
    if candidate.suffix in {".yml", ".yaml"} and candidate.exists():
        return candidate.read_text(encoding="utf-8")
    return source


def _safe_load_documents(text: str) -> list[list[dict[str, Any]]]:
    try:
        documents = list(yaml.safe_load_all(text))
    except yaml.YAMLError as error:
        raise InvalidPolicyError(f"Could not parse policy YAML: {error}") from error
    normalized: list[list[dict[str, Any]]] = []
    for document in documents:
        if document is None:
            continue
        if isinstance(document, list):
            normalized.append(document)
        elif isinstance(document, dict):
            normalized.append([document])
        else:
            raise InvalidPolicyError(
                f"Each YAML document must be a policy mapping or a list of them, got "
                f"{type(document).__name__}."
            )
    return normalized
