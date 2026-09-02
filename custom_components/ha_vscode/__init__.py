"""Set up and unload the VS Code tunnel."""

from .const import DOMAIN, PLATFORMS


async def async_setup(hass, config):
    return True


async def async_setup_entry(hass, config_entry):
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    config_entry.async_on_unload(config_entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass, config_entry):
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass, config_entry):
    unloaded = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(config_entry.entry_id, None)
    return unloaded
