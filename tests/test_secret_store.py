from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pytest

from target_agent import secret_store
from target_agent.settings import Settings, load_settings


class FakeKeyring:
    def __init__(self):
        self.values: dict[str, str] = {}
        self.backend = SimpleNamespace(name="FakeKeyringBackend")

    def get_password(self, service, name):
        return self.values.get(name)

    def set_password(self, service, name, value):
        self.values[name] = value

    def delete_password(self, service, name):
        self.values.pop(name, None)

    def get_keyring(self):
        return self.backend


@pytest.fixture
def fake_keyring(monkeypatch):
    fake = FakeKeyring()
    monkeypatch.setattr(secret_store, "_backend", lambda: fake)
    return fake


def test_get_set_delete_secret_roundtrip(fake_keyring):
    assert secret_store.get_secret("STEP_API_KEY") is None
    assert secret_store.set_secret("STEP_API_KEY", "key-123") is True
    assert secret_store.get_secret("STEP_API_KEY") == "key-123"
    assert secret_store.keyring_backend_name() == "FakeKeyringBackend"
    assert secret_store.delete_secret("STEP_API_KEY") is True
    assert secret_store.get_secret("STEP_API_KEY") is None


def test_secret_store_failure_soft_without_backend(monkeypatch):
    monkeypatch.setattr(secret_store, "_backend", lambda: None)
    assert secret_store.get_secret("STEP_API_KEY") is None
    assert secret_store.keyring_backend_name() is None
    assert secret_store.delete_secret("STEP_API_KEY") is False
    with pytest.raises(RuntimeError, match="not available"):
        secret_store.set_secret("STEP_API_KEY", "x")


def test_set_secret_validates_input(fake_keyring):
    with pytest.raises(ValueError, match="secret name"):
        secret_store.set_secret("", "x")
    with pytest.raises(ValueError, match="secret value"):
        secret_store.set_secret("STEP_API_KEY", "   ")


def test_settings_fill_missing_key_from_keyring(monkeypatch, tmp_path):
    monkeypatch.delenv("STEP_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    monkeypatch.setattr(
        secret_store,
        "get_secret",
        lambda name: "keyring-step-key" if name == "STEP_API_KEY" else None,
    )
    settings = load_settings(env_file=tmp_path / "missing.env")
    assert settings.step_api_key.get_secret_value() == "keyring-step-key"
    assert settings.step_configured is True


def test_settings_process_environment_beats_keyring(monkeypatch, tmp_path):
    monkeypatch.setenv("STEP_API_KEY", "env-step-key")
    monkeypatch.setattr(
        secret_store,
        "get_secret",
        lambda name: "keyring-step-key" if name == "STEP_API_KEY" else None,
    )
    settings = load_settings(env_file=tmp_path / "missing.env")
    assert settings.step_api_key.get_secret_value() == "env-step-key"


def test_doctor_reports_keyring_without_leaking_values(monkeypatch, capsys):
    import sys as sys_module

    from target_agent import cli

    monkeypatch.setattr(secret_store, "keyring_backend_name", lambda: "FakeKeyringBackend")
    monkeypatch.setattr(
        secret_store,
        "get_secret",
        lambda name: "secret-value" if name == "STEP_API_KEY" else None,
    )
    monkeypatch.setattr(sys_module, "argv", ["target-agent", "doctor"])
    cli.main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["keyring"]["backend"] == "FakeKeyringBackend"
    assert payload["keyring"]["secrets"]["STEP_API_KEY"] is True
    assert "secret-value" not in capsys.readouterr().out