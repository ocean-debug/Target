from __future__ import annotations

import json
import sys

import pytest

from target_agent import cli, secret_store


def _run_cli(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["target-agent", *argv])
    cli.main()


def test_up_runs_doctor_then_starts_workbench(monkeypatch, capsys, tmp_path):
    captured = {}

    def fake_doctor(settings):
        return {
            "required_dependencies": {name: True for name in ("flask", "waitress", "pydantic")},
            "settings": {
                "llm_configured": True,
                "projects_dir_writable": True,
            },
            "keyring": {"backend": "FakeKeyringBackend"},
        }

    def fake_start(settings, args):
        captured["port"] = args.port
        captured["host"] = args.host

    monkeypatch.setattr(cli, "_doctor", fake_doctor)
    monkeypatch.setattr(cli, "_start_workbench", fake_start)
    _run_cli(
        monkeypatch,
        "up", "--port", "8899", "--projects-dir", str(tmp_path / "projects"),
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["start"] == "up"
    assert payload["llm_configured"] is True
    assert payload["keyring_backend"] == "FakeKeyringBackend"
    assert captured == {"port": 8899, "host": "127.0.0.1"}


def test_up_fails_fast_when_required_dependency_missing(monkeypatch, tmp_path):
    def fake_doctor(settings):
        return {
            "required_dependencies": {
                "flask": True,
                "waitress": False,
                "pydantic": True,
            },
            "settings": {"llm_configured": True, "projects_dir_writable": True},
            "keyring": {"backend": None},
        }

    monkeypatch.setattr(cli, "_doctor", fake_doctor)

    def fail_if_started(settings, args):
        raise AssertionError("workbench must not start when required deps are missing")

    monkeypatch.setattr(cli, "_start_workbench", fail_if_started)
    with pytest.raises(SystemExit, match="waitress"):
        _run_cli(monkeypatch, "up", "--port", "8899", "--projects-dir", str(tmp_path / "projects"))


def test_secrets_status_cli(monkeypatch, capsys):
    monkeypatch.setattr(secret_store, "keyring_backend_name", lambda: "FakeKeyringBackend")
    monkeypatch.setattr(
        secret_store,
        "get_secret",
        lambda name: "configured-value" if name == "STEP_API_KEY" else None,
    )
    _run_cli(monkeypatch, "secrets", "status")
    payload = json.loads(capsys.readouterr().out)
    assert payload["backend"] == "FakeKeyringBackend"
    assert payload["secrets"]["STEP_API_KEY"] == "configured"
    assert payload["secrets"]["OPENAI_API_KEY"] == "not_configured"
    assert "configured-value" not in capsys.readouterr().out


def test_secrets_set_and_delete_cli(monkeypatch, capsys):
    stored = {}

    def fake_set(name, value):
        stored[name] = value
        return True

    def fake_delete(name):
        return stored.pop(name, None) is not None

    monkeypatch.setattr(secret_store, "set_secret", fake_set)
    monkeypatch.setattr(secret_store, "delete_secret", fake_delete)
    _run_cli(monkeypatch, "secrets", "set", "STEP_API_KEY", "--value", "key-456")
    assert json.loads(capsys.readouterr().out) == {"stored": True, "name": "STEP_API_KEY"}
    assert stored == {"STEP_API_KEY": "key-456"}
    _run_cli(monkeypatch, "secrets", "delete", "STEP_API_KEY")
    assert json.loads(capsys.readouterr().out) == {"deleted": True, "name": "STEP_API_KEY"}
    assert stored == {}