"""Switch controlling one CLI process, with separate readiness information."""

import asyncio
import re

from homeassistant.components import persistent_notification
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .exceptions import HAVSCodeException
from .vscode_device import TunnelBusyError, VSCodeDeviceAPI

AUTH_NOTIFICATION_ID = "ha_vscode_auth_required"
AUTH_NOTIFICATION_TITLE = "VS Code Tunnel authentication required"
AUTH_NOTIFICATION_MESSAGE = """The VS Code Tunnel needs GitHub authentication.

1. Turn off the tunnel switch.
2. Open **Settings → Devices & services → Home Assistant VSCode Tunnel**.
3. Select **Configure** and enable **Check authentication / sign in again**.
4. Submit the form and authorize the displayed code on GitHub.
5. Turn the tunnel switch on again after authentication succeeds.
"""
RETRY_DELAY = 3
RETRY_WINDOW = 10


async def async_setup_entry(hass, config, async_add_entities):
    data = {**config.data, **config.options}
    tunnel_name = re.sub(
        r"^https://vscode.dev/tunnel/", "", data["dev_url"]
    ).split("/")[0]
    device = VSCodeDeviceAPI(
        data["path"], hass.config.path(".ha_vscode"), tunnel_name
    )
    hass.data.setdefault(DOMAIN, {})[config.entry_id] = device
    async_add_entities([VSCodeEntity(device, config)])


class VSCodeEntity(SwitchEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, device, config):
        self.device = device
        self.config = config
        data = {**config.data, **config.options}
        name = re.sub(r"^https://vscode.dev/tunnel/", "", data["dev_url"]).split("/")[0]
        self._attr_name = "VSCode.dev Tunnel: " + name
        self._attr_unique_id = config.entry_id
        self._retry_task = None

    async def async_added_to_hass(self):
        self.device.set_status_callback(self._status_changed_from_thread)
        self.async_on_remove(
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self._async_stop)
        )
        self.async_on_remove(self._remove_status_callback)

    def _remove_status_callback(self):
        self.device.set_status_callback(None)
        if self._retry_task is not None:
            self._retry_task.cancel()

    def _status_changed_from_thread(self):
        """Move CLI reader updates safely onto the Home Assistant event loop."""
        self.hass.loop.call_soon_threadsafe(self._handle_status_change)

    def _handle_status_change(self):
        self.async_write_ha_state()
        if self.device.status == "ready":
            persistent_notification.async_dismiss(
                self.hass, AUTH_NOTIFICATION_ID
            )
            return
        if self.device.probe_owner is not None:
            return
        if self.device.status == "auth_required":
            persistent_notification.async_create(
                self.hass,
                AUTH_NOTIFICATION_MESSAGE,
                title=AUTH_NOTIFICATION_TITLE,
                notification_id=AUTH_NOTIFICATION_ID,
            )

    async def _async_stop(self, event=None):
        await self.hass.async_add_executor_job(self.device.stopTunnel)

    async def async_will_remove_from_hass(self):
        await self._async_stop()

    async def async_turn_on(self, **kwargs):
        retry_allowed = self.device.consume_retry_after_probe()
        try:
            await self.hass.async_add_executor_job(self.device.startTunnel)
        except TunnelBusyError as err:
            raise HomeAssistantError(
                "Finish or cancel the authentication check before starting the tunnel."
            ) from err
        except (HAVSCodeException, OSError) as err:
            raise HomeAssistantError(
                "Unable to install or start the VS Code CLI. Check network access and file permissions."
            ) from err
        self.async_write_ha_state()
        if retry_allowed:
            self._retry_task = self.hass.async_create_task(
                self._async_retry_after_authentication(),
                "Retry VS Code Tunnel after authentication",
            )

    async def _async_retry_after_authentication(self):
        """Retry once if the first post-authentication start exits with code 1."""
        try:
            deadline = self.hass.loop.time() + RETRY_WINDOW
            while self.hass.loop.time() < deadline:
                if self.device.status == "ready":
                    return
                if self.device.status == "stopped":
                    if self.device.last_exit_code != 1:
                        return
                    await asyncio.sleep(RETRY_DELAY)
                    await self.hass.async_add_executor_job(self.device.startTunnel)
                    self.async_write_ha_state()
                    return
                await asyncio.sleep(0.2)
        finally:
            self._retry_task = None

    async def async_turn_off(self, **kwargs):
        if self._retry_task is not None:
            self._retry_task.cancel()
            self._retry_task = None
        await self._async_stop()
        self.async_write_ha_state()

    @property
    def is_on(self):
        # On means the requested process runs; readiness is reported separately.
        return self.device.isRunning()

    @property
    def extra_state_attributes(self):
        return {
            "tunnel_status": self.device.status,
            "tunnel_url": self.device.devURL if self.device.status == "ready" else None,
            "last_error_category": self.device.last_error,
            "last_exit_code": self.device.last_exit_code,
            "configuration_in_progress": self.device.probe_owner is not None,
        }
