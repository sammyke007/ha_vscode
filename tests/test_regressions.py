"""Use real HA flow classes and subprocesses without contacting GitHub."""

import asyncio
import io
import subprocess
import sys
import tarfile
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.ha_vscode import async_unload_entry
from custom_components.ha_vscode import config_flow as flows
from custom_components.ha_vscode import vscode_device as api_module
from custom_components.ha_vscode.config_flow import (
    HAVSCodeFlowHandler,
    HAVSCodeOptionsFlowHandler,
)
from custom_components.ha_vscode.switch import VSCodeEntity
from custom_components.ha_vscode.vscode_device import TunnelBusyError, VSCodeDeviceAPI


@pytest.fixture
def hass(tmp_path, monkeypatch):
    async def executor(fn, *args):
        return fn(*args)

    monkeypatch.setattr(flows, "async_call_later", Mock(return_value=Mock()))
    return SimpleNamespace(
        data={},
        bus=SimpleNamespace(async_listen_once=Mock(return_value=Mock())),
        async_add_executor_job=AsyncMock(side_effect=executor),
        config=SimpleNamespace(path=lambda *parts: str(tmp_path.joinpath(*parts))),
    )


def device(state="starting"):
    return SimpleNamespace(
        claim_probe=Mock(),
        release_probe=Mock(),
        startTunnel=Mock(),
        wait_status=AsyncMock(return_value=state),
        devURL=None,
        oauthToken=None,
        last_error=None,
        last_exit_code=None,
        retry_after_probe=False,
    )


def options_flow(hass, api):
    entry = SimpleNamespace(
        entry_id="test",
        data={
            "path": "/existing/bin",
            "dev_url": "https://vscode.dev/tunnel/old/",
            "timeout": 7.0,
        },
        options={},
    )
    hass.config_entries = SimpleNamespace(async_get_known_entry=lambda _: entry)
    hass.data = {"ha_vscode": {"test": api}}
    flow = HAVSCodeOptionsFlowHandler()
    flow.hass = hass
    flow.handler = "test"
    return flow, entry


@pytest.mark.asyncio
async def test_opening_options_never_starts_or_checks(hass):
    api = device()
    flow, entry = options_flow(hass, api)
    entry.options = {"timeout": 12.0}
    result = await flow.async_step_init()
    assert result["type"] == "form"
    assert flow.timeout == 12
    api.startTunnel.assert_not_called()
    api.wait_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_settings_save_does_not_authenticate_or_discard_options(hass):
    api = device()
    flow, entry = options_flow(hass, api)
    entry.options = {"custom": "preserved", "token": "obsolete"}
    result = await flow.async_step_init({"timeout": 15})
    assert result["type"] == "create_entry"
    assert result["data"] == {"timeout": 15, "custom": "preserved"}
    api.startTunnel.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("timeout", [0, -1, 121, "invalid"])
async def test_invalid_timeout(hass, timeout):
    flow, _ = options_flow(hass, device())
    result = await flow.async_step_init({"timeout": timeout})
    assert result["errors"]["base"] == "invalid_timeout"


@pytest.mark.asyncio
async def test_late_auth_code_and_url_follow_same_session(hass):
    api = device()
    flow, _ = options_flow(hass, api)
    result = await flow.async_step_init({"timeout": 7, "check_auth": True})
    assert result["step_id"] == "wait"
    api.release_probe.assert_not_called()
    api.oauthToken = "ABCD-1234"
    api.wait_status.return_value = "auth_required"
    result = await flow.async_step_wait({})
    assert result["step_id"] == "authorize"
    assert result["description_placeholders"]["token"] == "ABCD-1234"
    result = await flow.async_step_authorize({})
    assert result["step_id"] == "authorize"
    api.release_probe.assert_not_called()
    api.wait_status.return_value = "ready"
    api.devURL = "https://vscode.dev/tunnel/new/"
    result = await flow.async_step_authorize({})
    assert result["data"]["dev_url"] == api.devURL
    api.startTunnel.assert_called_once()
    api.release_probe.assert_called_once()
    assert "token" not in result["data"]


@pytest.mark.asyncio
async def test_missing_token_and_url_never_claims_success(hass):
    flow, _ = options_flow(hass, device())
    result = await flow.async_step_init({"timeout": 7, "check_auth": True})
    assert result["type"] == "form" and result["step_id"] == "wait"


@pytest.mark.asyncio
async def test_running_or_reserved_tunnel_blocks_probe(hass):
    api = device()
    api.claim_probe.side_effect = TunnelBusyError
    flow, _ = options_flow(hass, api)
    result = await flow.async_step_init({"timeout": 7, "check_auth": True})
    assert result["reason"] == "tunnel_busy"
    api.startTunnel.assert_not_called()
    api.release_probe.assert_not_called()


@pytest.mark.asyncio
async def test_stopped_cli_aborts_and_releases(hass):
    api = device("stopped")
    flow, _ = options_flow(hass, api)
    result = await flow.async_step_init({"timeout": 7, "check_auth": True})
    assert result["reason"] == "tunnel_exited"
    api.release_probe.assert_called_once()


@pytest.mark.asyncio
async def test_start_failure_releases_reservation(hass):
    api = device()
    api.startTunnel.side_effect = OSError("test")
    flow, _ = options_flow(hass, api)
    result = await flow.async_step_init({"timeout": 7, "check_auth": True})
    assert result["reason"] == "cannot_start"
    api.release_probe.assert_called_once()


@pytest.mark.asyncio
async def test_expired_session_cannot_create_entry(hass):
    api = device()
    flow, _ = options_flow(hass, api)
    await flow.async_step_init({"timeout": 7, "check_auth": True})
    # Execute callback with a synchronous executor scheduler, like Home Assistant.
    hass.async_add_executor_job = lambda fn, *args: fn(*args)
    flow._expire(None)
    api.release_probe.assert_called_once()
    api.wait_status.return_value = "ready"
    result = await flow.async_step_wait({})
    assert result["reason"] == "session_expired"


@pytest.mark.asyncio
async def test_cancel_probe_releases_only_once(hass):
    api = device()
    flow, _ = options_flow(hass, api)
    await flow.async_step_init({"timeout": 7, "check_auth": True})
    hass.async_add_executor_job = lambda fn, *args: fn(*args)
    flow.async_remove()
    flow.async_remove()
    api.release_probe.assert_called_once()


@pytest.mark.asyncio
async def test_initial_setup_uses_entered_timeout(hass, monkeypatch):
    api = device()
    monkeypatch.setattr(flows, "VSCodeDeviceAPI", lambda *_: api)
    flow = HAVSCodeFlowHandler()
    flow.hass = hass
    flow._async_current_entries = list
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = Mock()
    result = await flow.async_step_user()
    assert result["step_id"] == "user"
    api.startTunnel.assert_not_called()
    result = await flow.async_step_user({"timeout": 11})
    assert result["step_id"] == "wait"
    api.wait_status.assert_awaited_once_with(11.0, after_auth=False)
    api.devURL = "https://vscode.dev/tunnel/new/"
    api.wait_status.return_value = "ready"
    result = await flow.async_step_wait({})
    assert result["type"] == "create_entry"
    assert result["data"]["timeout"] == 11
    assert "token" not in result["data"]


def test_reader_eof_and_redacted_categories(tmp_path, caplog):
    api = VSCodeDeviceAPI(str(tmp_path))
    stream = io.StringIO(
        "unauthorized bearer supersecret\nhttps://github.com/login/device and use code ABCD-1234\n"
    )
    api.reader(SimpleNamespace(stdout=stream, poll=lambda: 1))
    assert api.last_error == "authentication"
    assert api.oauthToken == "ABCD-1234"
    assert "supersecret" not in caplog.text and "ABCD-1234" not in caplog.text
    assert "code=1" in caplog.text


def test_parser_clears_stale_state_and_strips_ansi(tmp_path):
    api = VSCodeDeviceAPI(str(tmp_path))
    api.devURL = "old"
    text = "https://github.com/login/device and use code \x1b[1mABCD-1234\x1b[0m\nhttps://vscode.dev/tunnel/test-name/\n"
    api.reader(SimpleNamespace(stdout=io.StringIO(text), poll=lambda: None))
    assert api.devURL == "https://vscode.dev/tunnel/test-name/"
    assert api.oauthToken is None


def test_successful_probe_enables_exactly_one_retry(tmp_path):
    api = VSCodeDeviceAPI(str(tmp_path))
    api.probe_owner = object()
    api.checkForDevURL("https://vscode.dev/tunnel/test/")
    assert api.consume_retry_after_probe()
    assert not api.consume_retry_after_probe()


def test_authentication_status_callback_contains_no_device_code(tmp_path):
    api = VSCodeDeviceAPI(str(tmp_path))
    callback = Mock()
    api.set_status_callback(callback)
    api.checkForOauthToken(
        "https://github.com/login/device and use code ABCD-1234"
    )
    callback.assert_called_once_with()


def test_start_stop_and_probe_exclusion(tmp_path):
    executable = tmp_path / "code"
    executable.write_text("#!/bin/sh\nexec sleep 60\n")
    executable.chmod(0o755)
    api = VSCodeDeviceAPI(str(tmp_path))
    owner = object()
    api.claim_probe(owner)
    try:
        with pytest.raises(TunnelBusyError):
            api.startTunnel()
        with pytest.raises(TunnelBusyError):
            api.claim_probe(object())
        api.startTunnel(owner)
        proc, thread = api.proc, api.thread
        api.startTunnel(owner)
        assert api.proc is proc
        api.release_probe(object())
        assert api.isRunning()
        api.release_probe(owner)
        assert proc.poll() is not None and not thread.is_alive()
        assert api.probe_owner is None
        with pytest.raises(TunnelBusyError):
            api.startTunnel(owner)
    finally:
        api.stopTunnel()


def test_tunnel_uses_persistent_runtime_directories(tmp_path):
    runtime = tmp_path / ".ha_vscode"
    api = VSCodeDeviceAPI(
        str(tmp_path / "component-bin"), runtime, "homeassistant"
    )
    api.prepare_runtime()
    command = api.tunnel_command()

    assert command == [
        str(tmp_path / "component-bin" / "code"),
        "--cli-data-dir",
        str(runtime / "cli"),
        "tunnel",
        "--server-data-dir",
        str(runtime / "server"),
        "--extensions-dir",
        str(runtime / "extensions"),
        "--name",
        "homeassistant",
        "--accept-server-license-terms",
    ]
    for directory in (runtime, runtime / "cli", runtime / "server", runtime / "extensions"):
        assert directory.is_dir()
        assert directory.stat().st_mode & 0o777 == 0o700


def test_dead_process_not_ready(tmp_path):
    api = VSCodeDeviceAPI(str(tmp_path))
    api.proc = subprocess.Popen(
        [sys.executable, "-c", "pass"], stdout=subprocess.PIPE, start_new_session=True
    )
    api.proc.wait(timeout=5)
    api.devURL = "https://vscode.dev/tunnel/stale/"
    assert api.status == "stopped"
    api.stopTunnel()


@pytest.mark.asyncio
async def test_wait_status_detects_late_token_and_url(tmp_path):
    api = VSCodeDeviceAPI(str(tmp_path))
    api.isRunning = lambda: True

    async def later():
        await asyncio.sleep(0.01)
        api.checkForOauthToken("https://github.com/login/device and use code ABCD-1234")

    task = asyncio.create_task(later())
    assert await api.wait_status(1) == "auth_required"
    await task

    async def ready():
        await asyncio.sleep(0.01)
        api.checkForDevURL("https://vscode.dev/tunnel/test/")

    task = asyncio.create_task(ready())
    assert await api.wait_status(1, after_auth=True) == "ready"
    await task


def test_install_extracts_only_binary(tmp_path, monkeypatch):
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as tar:
        for name, content in [("code", b"cli"), ("../escape", b"no")]:
            member = tarfile.TarInfo(name)
            member.size = len(content)
            tar.addfile(member, io.BytesIO(content))
    archive.seek(0)
    monkeypatch.setattr(api_module, "urlopen", lambda *args, **kwargs: archive)
    api = VSCodeDeviceAPI(str(tmp_path / "bin"))
    api.install()
    assert (tmp_path / "bin/code").read_bytes() == b"cli"
    assert not (tmp_path / "escape").exists()


def test_switch_separates_running_from_ready(tmp_path):
    api = VSCodeDeviceAPI(str(tmp_path))
    api.isRunning = lambda: True
    entry = SimpleNamespace(
        entry_id="test", data={"dev_url": "https://vscode.dev/tunnel/old/"}, options={}
    )
    entity = VSCodeEntity(api, entry)
    assert entity.is_on
    assert entity.extra_state_attributes["tunnel_status"] == "starting"
    assert entity.extra_state_attributes["tunnel_url"] is None
    api.oauthToken = "ABCD-1234"
    assert entity.extra_state_attributes["tunnel_status"] == "auth_required"
    assert "ABCD-1234" not in str(entity.extra_state_attributes)


def test_switch_creates_and_clears_auth_notification(tmp_path, monkeypatch):
    api = VSCodeDeviceAPI(str(tmp_path))
    api.isRunning = lambda: True
    entry = SimpleNamespace(
        entry_id="test", data={"dev_url": "https://vscode.dev/tunnel/old/"}, options={}
    )
    entity = VSCodeEntity(api, entry)
    entity.hass = object()
    entity.async_write_ha_state = Mock()
    create = Mock()
    dismiss = Mock()
    monkeypatch.setattr(
        "custom_components.ha_vscode.switch.persistent_notification.async_create",
        create,
    )
    monkeypatch.setattr(
        "custom_components.ha_vscode.switch.persistent_notification.async_dismiss",
        dismiss,
    )

    api.oauthToken = "ABCD-1234"
    entity._handle_status_change()
    create.assert_called_once()
    assert "ABCD-1234" not in str(create.call_args)

    api.oauthToken = None
    api.devURL = "https://vscode.dev/tunnel/test/"
    entity._handle_status_change()
    dismiss.assert_called_once_with(entity.hass, "ha_vscode_auth_required")


@pytest.mark.asyncio
async def test_first_post_auth_exit_code_one_is_retried_once(monkeypatch):
    api = SimpleNamespace(
        status="stopped", last_exit_code=1, startTunnel=Mock()
    )
    entry = SimpleNamespace(
        entry_id="test", data={"dev_url": "https://vscode.dev/tunnel/old/"}, options={}
    )
    entity = VSCodeEntity(api, entry)
    loop = asyncio.get_running_loop()

    async def executor(fn, *args):
        return fn(*args)

    entity.hass = SimpleNamespace(loop=loop, async_add_executor_job=executor)
    entity.async_write_ha_state = Mock()
    monkeypatch.setattr("custom_components.ha_vscode.switch.RETRY_DELAY", 0)
    await entity._async_retry_after_authentication()
    api.startTunnel.assert_called_once_with()


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
async def test_startup_cancellation_releases_probe(hass):
    api = device()
    flow, _ = options_flow(hass, api)

    async def executor(fn, *args):
        if fn is api.startTunnel:
            raise asyncio.CancelledError
        return fn(*args)

    # HA schedules executor futures immediately; capture cleanup scheduling.
    def schedule(fn, *args):
        return asyncio.create_task(executor(fn, *args))

    hass.async_add_executor_job = schedule
    with pytest.raises(asyncio.CancelledError):
        await flow.async_step_init({"timeout": 7, "check_auth": True})
    await asyncio.sleep(0)
    assert api.release_probe.call_count >= 1


def test_stop_reaps_child_that_keeps_stdout_open(tmp_path):
    import os

    api = VSCodeDeviceAPI(str(tmp_path))
    api.proc = subprocess.Popen(
        [sys.executable, "-c", "import subprocess; subprocess.Popen(['sleep','60'])"],
        stdout=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    process = api.proc
    try:
        process.wait(timeout=5)
        api.stopTunnel()
        assert api.proc is None
        assert process.stdout.closed
    finally:
        try:
            os.killpg(process.pid, 9)
        except ProcessLookupError:
            pass


def test_start_recovers_missing_cli(tmp_path, monkeypatch):
    api = VSCodeDeviceAPI(str(tmp_path))

    def install():
        executable = tmp_path / "code"
        executable.write_text("#!/bin/sh\nexec sleep 60\n")
        executable.chmod(0o755)

    monkeypatch.setattr(api, "install", install)
    try:
        api.startTunnel()
        assert api.isRunning()
    finally:
        api.stopTunnel()


@pytest.mark.asyncio
async def test_cancel_during_claim_cannot_orphan_reservation(hass):
    api = device()
    flow, _ = options_flow(hass, api)
    entered, finish = asyncio.Event(), asyncio.Event()

    async def executor(fn, *args):
        if fn is api.claim_probe:
            entered.set()
            await finish.wait()
        return fn(*args)

    hass.async_add_executor_job = lambda fn, *args: asyncio.create_task(
        executor(fn, *args)
    )
    task = asyncio.create_task(flow.async_step_init({"timeout": 7, "check_auth": True}))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    finish.set()
    for _ in range(5):
        await asyncio.sleep(0)
    api.claim_probe.assert_called_once()
    api.release_probe.assert_called_once()
    api.startTunnel.assert_not_called()
