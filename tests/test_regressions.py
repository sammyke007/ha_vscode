"""Regression tests using real HA flow classes and local child processes."""

import io
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.ha_vscode import async_unload_entry
from custom_components.ha_vscode.config_flow import HAVSCodeFlowHandler
from custom_components.ha_vscode.switch import async_setup_entry
from custom_components.ha_vscode.vscode_device import VSCodeDeviceAPI


def test_reader_stops_at_eof(tmp_path):
    api = VSCodeDeviceAPI(str(tmp_path))
    stream = io.StringIO("Open https://vscode.dev/tunnel/test-name\n")
    api.reader(SimpleNamespace(stdout=stream))
    assert api.devURL == "https://vscode.dev/tunnel/test-name"


def test_token_parser(tmp_path, caplog):
    api = VSCodeDeviceAPI(str(tmp_path))
    assert (
        api.checkForOauthToken("https://github.com/login/device and use code ABCD-1234")
        == "ABCD-1234"
    )
    assert "ABCD-1234" not in caplog.text


def test_dead_process_is_off(tmp_path):
    api = VSCodeDeviceAPI(str(tmp_path))
    api.proc = subprocess.Popen(
        [sys.executable, "-c", "pass"], stdout=subprocess.PIPE, start_new_session=True
    )
    api.proc.wait(timeout=5)
    assert not api.isRunning()
    api.stopTunnel()
    assert api.proc is None


def test_start_stop_is_idempotent(tmp_path):
    executable = tmp_path / "code"
    executable.write_text("#!/bin/sh\nexec sleep 60\n")
    executable.chmod(0o755)
    api = VSCodeDeviceAPI(str(tmp_path))
    try:
        api.startTunnel()
        proc = api.proc
        thread = api.thread
        api.startTunnel()
        assert api.proc is proc
        assert api.isRunning()
        api.stopTunnel()
        assert proc.poll() is not None
        assert not thread.is_alive()
        api.stopTunnel()
    finally:
        api.stopTunnel()


@pytest.mark.asyncio
async def test_options_uses_framework_entry_and_data_fallback(tmp_path):
    entry = SimpleNamespace(
        entry_id="test",
        data={
            "path": str(tmp_path),
            "dev_url": "https://vscode.dev/tunnel/demo/",
            "timeout": 5.0,
        },
        options={"timeout": 12.0},
    )
    flow = HAVSCodeFlowHandler.async_get_options_flow(entry)
    flow.hass = SimpleNamespace(
        data={
            "ha_vscode": {"test": SimpleNamespace(isRunning=lambda: True, devURL=None)}
        },
        config_entries=SimpleNamespace(async_get_known_entry=lambda _: entry),
    )
    flow.handler = "test"
    result = await flow.async_step_init()
    assert result["type"] == "form"
    assert flow.path == str(tmp_path)
    assert flow.timeout == 12.0
    result = await flow.async_step_user({"timeout": 20.0})
    assert result["type"] == "create_entry"
    assert result["data"]["timeout"] == 20.0
    assert result["data"]["path"] == str(tmp_path)


@pytest.mark.asyncio
async def test_switch_uses_options(tmp_path):
    hass = SimpleNamespace(data={})
    entry = SimpleNamespace(
        entry_id="test",
        data={"path": "old", "dev_url": "https://vscode.dev/tunnel/old/"},
        options={"path": str(tmp_path), "dev_url": "https://vscode.dev/tunnel/new/"},
    )
    add = Mock()
    await async_setup_entry(hass, entry, add)
    entity = add.call_args.args[0][0]
    assert entity.device.storage_dir == str(tmp_path)
    assert entity.unique_id == "test"
    assert "new" in entity.name


@pytest.mark.asyncio
async def test_unload_failure_retains_device():
    hass = SimpleNamespace(
        data={"ha_vscode": {"test": object()}},
        config_entries=SimpleNamespace(
            async_unload_platforms=AsyncMock(return_value=False)
        ),
    )
    assert not await async_unload_entry(hass, SimpleNamespace(entry_id="test"))
    assert "test" in hass.data["ha_vscode"]


@pytest.mark.asyncio
async def test_activation_stops_probe_before_entry(tmp_path):
    flow = HAVSCodeFlowHandler()

    async def executor(fn, *args):
        return fn(*args)

    flow.hass = SimpleNamespace(async_add_executor_job=executor)
    flow.device = SimpleNamespace(
        activate=AsyncMock(return_value="https://vscode.dev/tunnel/test/"),
        stopTunnel=Mock(),
    )
    flow.path = str(tmp_path)
    flow.oauthToken = "ABCD-1234"
    result = await flow.async_step_activate({})
    assert result["type"] == "create_entry"
    flow.device.stopTunnel.assert_called_once()


@pytest.mark.asyncio
async def test_reauth_saves_result():
    flow = HAVSCodeFlowHandler.async_get_options_flow(None)

    async def executor(fn, *args):
        return fn(*args)

    flow.hass = SimpleNamespace(async_add_executor_job=executor)
    flow.device = SimpleNamespace(
        getDevURL=AsyncMock(return_value="https://vscode.dev/tunnel/new/"),
        stopTunnel=Mock(),
    )
    result = await flow.async_step_reauth({})
    assert result["type"] == "create_entry"
    assert result["data"]["dev_url"] == "https://vscode.dev/tunnel/new/"
    flow.device.stopTunnel.assert_called_once()


def test_install_extracts_only_binary(tmp_path, monkeypatch):
    import tarfile

    from custom_components.ha_vscode import vscode_device

    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as tar:
        for name, content in [("code", b"cli"), ("../escape", b"no")]:
            member = tarfile.TarInfo(name)
            member.size = len(content)
            tar.addfile(member, io.BytesIO(content))
    archive.seek(0)
    monkeypatch.setattr(vscode_device, "urlopen", lambda *args, **kwargs: archive)
    api = VSCodeDeviceAPI(str(tmp_path / "bin"))
    api.install()
    assert (tmp_path / "bin/code").read_bytes() == b"cli"
    assert not (tmp_path / "escape").exists()
