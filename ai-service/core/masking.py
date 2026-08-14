"""Masking of personal data before it reaches any log line."""

from typing import Any, Dict

_SENSITIVE_KEYS = {"phone", "email"}


def mask_sensitive_args(args: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of args with personal-data values replaced by ***."""
    return {key: ("***" if key in _SENSITIVE_KEYS else value) for key, value in args.items()}
