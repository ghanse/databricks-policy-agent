"""Helpers for the tags stamped onto every object the policy agent creates.

A managed marker tag is always present so operators can find and audit policy-agent-owned
objects; user-supplied tags are merged on top.
"""

from __future__ import annotations

import json

MANAGED_BY_TAG = "managed_by"
MANAGED_BY_VALUE = "policy-agent"


def managed_tags(extra_tags: dict[str, str] | None = None) -> dict[str, str]:
    """Return the managed marker tag merged with any extra tags.

    Args:
        extra_tags: Additional tags to apply; these override the marker on key collision.

    Returns:
        A tag mapping that always includes the managed marker.
    """
    return {MANAGED_BY_TAG: MANAGED_BY_VALUE, **(extra_tags or {})}


def parse_tags(raw: str) -> dict[str, str]:
    """Parse tags from a string in either JSON object or ``key=value,key=value`` form.

    Args:
        raw: The raw tag string; an empty string yields no tags.

    Returns:
        The parsed tag mapping.
    """
    text = raw.strip()
    if not text:
        return {}
    if text.startswith("{"):
        return {str(key): str(value) for key, value in json.loads(text).items()}
    pairs = (segment.split("=", 1) for segment in text.split(",") if "=" in segment)
    return {key.strip(): value.strip() for key, value in pairs}
