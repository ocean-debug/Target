"""Optional OS-keyring secret storage for API keys.

Resolution order: process environment -> dotenv file -> OS keyring.
The keyring backend is optional and failure-soft: when unavailable, lookups
return None and the system continues with .env/process-env only. Values are
never logged, printed or written into traces/reports by this module.
"""
from __future__ import annotations

import importlib.util

SERVICE_NAME = "target-agent"
SECRET_NAMES = ("STEP_API_KEY", "OPENAI_API_KEY", "NCBI_API_KEY")


def _backend():
    if importlib.util.find_spec("keyring") is None:
        return None
    try:
        import keyring  # type: ignore
        return keyring
    except Exception:
        return None


def keyring_backend_name() -> str | None:
    keyring = _backend()
    if keyring is None:
        return None
    try:
        backend = keyring.get_keyring()
        return getattr(backend, "name", None) or type(backend).__name__
    except Exception:
        return None


def get_secret(name: str) -> str | None:
    keyring = _backend()
    if keyring is None:
        return None
    try:
        value = keyring.get_password(SERVICE_NAME, name)
        return value if isinstance(value, str) and value.strip() else None
    except Exception:
        return None


def set_secret(name: str, value: str) -> bool:
    name = name.strip()
    if not name or not name.replace("_", "").isalnum():
        raise ValueError("secret name must be a non-empty identifier")
    if not value or not value.strip():
        raise ValueError("secret value must not be empty")
    keyring = _backend()
    if keyring is None:
        raise RuntimeError(
            "OS keyring backend is not available; use an untracked .env file instead"
        )
    try:
        keyring.set_password(SERVICE_NAME, name, value)
        return True
    except Exception as exc:
        raise RuntimeError(f"failed to store secret in OS keyring: {exc}") from exc


def delete_secret(name: str) -> bool:
    keyring = _backend()
    if keyring is None:
        return False
    try:
        keyring.delete_password(SERVICE_NAME, name.strip())
        return True
    except Exception:
        return False


__all__ = [
    "SECRET_NAMES",
    "delete_secret",
    "get_secret",
    "keyring_backend_name",
    "set_secret",
]