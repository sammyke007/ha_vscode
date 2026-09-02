NAME = "HA VSCode Tunnel"
DOMAIN = "ha_vscode"
PACKAGE_NAME = "custom_components.ha_vscode"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.1.52"
MINIMUM_HA_VERSION = "2024.11.0"
ICON = "mdi:format-quote-close"
CONF_ENABLED = "enabled"
DEFAULT_NAME = DOMAIN
HAVSCODE_SYSTEM_ID = "98450013-1865-4292-be24-abde34214bd6"
ISSUE_URL = "https://github.com/sammyke007/ha_vscode/issues"
SWITCH = "switch"
PLATFORMS = [SWITCH]


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
