"""Switch controlling the tunnel process."""

import re

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.const import EVENT_HOMEASSISTANT_STOP

from .const import DOMAIN
from .vscode_device import VSCodeDeviceAPI


async def async_setup_entry(hass, config, async_add_entities):
    data = {**config.data, **config.options}
    device = VSCodeDeviceAPI(data["path"])
    hass.data.setdefault(DOMAIN, {})[config.entry_id] = device
    async_add_entities([VSCodeEntity(device, data["dev_url"], config.entry_id)])


class VSCodeEntity(SwitchEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, device, dev_url, entry_id):
        self.device = device
        name = re.sub(r"^https://vscode.dev/tunnel/", "", dev_url).split("/")[0]
        self._attr_name = "VSCode.dev Tunnel: " + name
        self._attr_unique_id = entry_id

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self._async_stop)
        )

    async def _async_stop(self, event=None):
        await self.hass.async_add_executor_job(self.device.stopTunnel)

    async def async_will_remove_from_hass(self):
        await self._async_stop()

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(self.device.startTunnel)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self._async_stop()
        self.async_write_ha_state()

    @property
    def is_on(self):
        return self.device.isRunning()
