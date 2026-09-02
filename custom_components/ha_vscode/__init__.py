"""Set up and unload the VS Code tunnel."""

from .const import DOMAIN, PLATFORMS


async def async_setup(hass, config):
    return True


async def async_setup_entry(hass, config_entry):
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass, config_entry):
    unloaded = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(config_entry.entry_id, None)
    return unloaded
