from __future__ import annotations

import re
from typing import Any

SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "api_secret",
        "password",
        "secret",
        "token",
        "authorization",
        "credential",
        "private_key",
    }
)

REDACTED = "***REDACTED***"


def sanitize_dict(data: dict[str, Any], extra_keys: frozenset[str] | None = None) -> dict[str, Any]:
    """Recursively redact sensitive fields from a dictionary.

    Args:
        data: The dictionary to sanitize.
        extra_keys: Additional key names to treat as sensitive.

    Returns:
        A new dictionary with sensitive values replaced by REDACTED.
    """
    keys_to_redact = SENSITIVE_KEYS | (extra_keys or frozenset())
    result: dict[str, Any] = {}

    for key, value in data.items():
        if key.lower() in keys_to_redact:
            result[key] = REDACTED
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value, extra_keys)
        elif isinstance(value, list):
            result[key] = [
                sanitize_dict(item, extra_keys) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value

    return result


def redact_string(value: str, pattern: str | None = None) -> str:
    """Redact sensitive patterns from a string.

    By default, redacts common API key patterns.
    """
    if pattern:
        return re.sub(pattern, REDACTED, value)

    # Redact common API key patterns (sk-..., key-..., etc.)
    value = re.sub(
        r"(sk|key|token|secret|password)[-_][\w]{8,}", REDACTED, value, flags=re.IGNORECASE
    )
    return value
