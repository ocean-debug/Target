from __future__ import annotations

import time

import pytest

from target_agent.kernel import (
    KernelDisabledError, KernelManager, KernelNotConfiguredError, KernelTimeoutError,
)
from target_agent.settings import Settings

from .test_research_runtime import fake_research_runtime, research_project
from .test_runtime import fake_runtime as fake_target_runtime


def _settings(tmp_path, **overrides):
    values = {
        "_env_file": None,
        "TARGET_AGENT_RUN_DIR": tmp_path / "runs",
        "RESEARCH_AGENT_PROJECT_DIR": tmp_path / "projects",
        "TARGET_AGENT_CACHE_DIR": tmp_path / "cache",
        "TARGET_AGENT_CACHE_ONLY": True,
    }
    values.update(overrides)
    return Settings(**values)


def test_python_kernel_persists_state_and_captures_output(tmp_path):
    manager = KernelManager(_settings(tmp_path))
    info = manager.create(language="python", cwd=tmp_path)
    assert info.status.value == "ready"
    assert info.language == "python"

    first = manager.execute(info.kernel_id, "x = 40\nprint('hello kernel')")
    assert first.ok is True
    assert first.stdout.strip() == "hello kernel"
    assert first.result is None

    second = manager.execute(info.kernel_id, "__kernel_result__ = x + 2")
    assert second.ok is True
    assert second.result == 42

    status = manager.get(info.kernel_id)
    assert status.exec_count == 2
    manager.stop_all()


def test_python_kernel_reports_errors_without_killing_session(tmp_path):
    manager = KernelManager(_settings(tmp_path))
    info = manager.create(language="python", cwd=tmp_path)

    failed = manager.execute(info.kernel_id, "raise ValueError('boom')")
    assert failed.ok is False
    assert failed.error == "ValueError"
    assert "boom" in (failed.message or "")

    still_alive = manager.execute(info.kernel_id, "__kernel_result__ = 7")
    assert still_alive.ok is True
    assert still_alive.result == 7
    manager.stop_all()


def test_python_kernel_timeout_kills_session_with_reason(tmp_path):
    manager = KernelManager(_settings(tmp_path))
    info = manager.create(language="python", cwd=tmp_path)

    with pytest.raises(KernelTimeoutError, match="exceeded"):
        manager.execute(info.kernel_id, "import time; time.sleep(5)", timeout=1)

    status = manager.get(info.kernel_id)
    assert status.status.value == "failed"
    assert "exceeded" in (status.error or "")
    manager.stop_all()


def test_kernel_output_truncation_marks_result(tmp_path):
    manager = KernelManager(_settings(tmp_path, TARGET_AGENT_KERNEL_MAX_OUTPUT_CHARS=1000))
    info = manager.create(language="python", cwd=tmp_path)

    result = manager.execute(info.kernel_id, "print('x' * 100000)")
    assert result.ok is True
    assert result.output_truncated is True
    assert "[truncated by target-agent kernel]" in result.stdout
    assert len(result.stdout) < 2000
    manager.stop_all()


def test_kernel_default_cwd_is_auto_created(tmp_path):
    manager = KernelManager(_settings(tmp_path))
    info = manager.create(language="python")
    assert info.status.value == "ready"
    assert (tmp_path / "projects").is_dir()
    manager.stop_all()


def test_kernel_disabled_raises_cleanly(tmp_path):
    manager = KernelManager(_settings(tmp_path, TARGET_AGENT_KERNEL_ENABLED=False))
    with pytest.raises(KernelDisabledError):
        manager.create(language="python", cwd=tmp_path)


def test_r_kernel_not_configured_raises_cleanly(tmp_path):
    manager = KernelManager(_settings(tmp_path, TARGET_AGENT_KERNEL_R="/nonexistent/Rscript"))
    with pytest.raises(KernelNotConfiguredError, match="Rscript"):
        manager.create(language="r", cwd=tmp_path)


def test_idle_kernels_are_reaped(tmp_path):
    manager = KernelManager(_settings(tmp_path, TARGET_AGENT_KERNEL_IDLE_TIMEOUT_SECONDS=1))
    info = manager.create(language="python", cwd=tmp_path)
    manager.execute(info.kernel_id, "x = 1")
    time.sleep(1.2)

    assert manager.reap_idle() == 1
    assert manager.list() == []


def test_web_kernel_api_lifecycle_and_capabilities(tmp_path):
    from target_agent.webapp import create_app

    research_runtime, calls = fake_research_runtime(tmp_path)
    app = create_app(fake_target_runtime(tmp_path), research_runtime=research_runtime)
    client = app.test_client()

    capabilities = client.get("/api/capabilities").get_json()
    assert capabilities["kernels"]["enabled"] is True
    assert capabilities["kernels"]["backends"]["python"] is True

    created = client.post("/api/kernels", json={"language": "python", "cwd": str(tmp_path)})
    assert created.status_code == 201
    kernel_id = created.get_json()["kernel_id"]

    listing = client.get("/api/kernels").get_json()
    assert [row["kernel_id"] for row in listing["kernels"]] == [kernel_id]

    executed = client.post(
        f"/api/kernels/{kernel_id}/exec",
        json={"code": "__kernel_result__ = [i * i for i in range(4)]"},
    )
    assert executed.status_code == 200
    assert executed.get_json()["result"] == [0, 1, 4, 9]

    missing = client.post("/api/kernels/kernel-does-not-exist/exec", json={"code": "x = 1"})
    assert missing.status_code == 404

    stopped = client.delete(f"/api/kernels/{kernel_id}")
    assert stopped.status_code == 200
    assert stopped.get_json()["status"] == "stopped"
    assert client.get("/api/kernels").get_json()["kernels"] == []
