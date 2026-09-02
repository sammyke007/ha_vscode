"""Switch controlling one CLI process, with separate readiness information."""

import re

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .exceptions import HAVSCodeException
from .vscode_device import TunnelBusyError, VSCodeDeviceAPI


async def async_setup_entry(hass, config, async_add_entities):
    data = {**config.data, **config.options}
    device = VSCodeDeviceAPI(data["path"])
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

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self._async_stop)
        )

    async def _async_stop(self, event=None):
        await self.hass.async_add_executor_job(self.device.stopTunnel)

    async def async_will_remove_from_hass(self):
        await self._async_stop()

    async def async_turn_on(self, **kwargs):
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

    async def async_turn_off(self, **kwargs):
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
            "configuration_in_progress": self.device.probe_owner is not None,
        }
