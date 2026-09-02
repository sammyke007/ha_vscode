"""Adds config flow for VSCode HA Tunnel."""

import logging
import os.path

import voluptuous as vol
from awesomeversion import AwesomeVersion
from homeassistant import config_entries
from homeassistant.const import __version__ as HAVERSION
from homeassistant.core import callback

from .const import *
from .exceptions import *
from .vscode_device import VSCodeDeviceAPI

LOGGER: logging.Logger = logging.getLogger(PACKAGE_NAME)


class HAVSCodeFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for ha_vscode."""

    VERSION = 1

    def __init__(self):
        """Initialize."""
        self._error = None
        self.device = None
        self.oauthToken = None
        self.devURL = None
        self.log = LOGGER
        self.path = None
        self.activate = False
        self.timeout = 5.0

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if self.hass.data.get(DOMAIN):
            return self.async_abort(reason="single_instance_allowed")

        if AwesomeVersion(HAVERSION) < MINIMUM_HA_VERSION:
            return self.async_abort(
                reason="min_ha_version",
                description_placeholders={"version": MINIMUM_HA_VERSION},
            )

        if self.path is None:
            self.path = os.path.join(self.hass.config.path("custom_components"), DOMAIN)
            self.path = os.path.join(self.path, "bin")
            self.log.info("bin directory located at: " + self.path)

        if self.device is None:
            self.device = VSCodeDeviceAPI(self.path)
            try:
                response = await self.device.register(timeout=self.timeout)
            except (HAVSCodeException, OSError):
                await self.hass.async_add_executor_job(self.device.stopTunnel)
                return self.async_abort(reason="download")
            if response is None:
                # check to see if we are somehow already authenticated
                response = await self.device.getDevURL(timeout=self.timeout)
                if response is None:
                    self._error = HAVSCodeAuthenticationException()
                else:
                    self.devURL = response
            else:
                self.oauthToken = response

        if self._error is not None:
            await self.hass.async_add_executor_job(self.device.stopTunnel)
            return self.async_abort(reason=self.reason_for_error())
        if self.oauthToken is not None and self.activate:
            return await self.async_step_activate(user_input)
        elif self.devURL is not None:
            # set the auth token to "already_registered"
            self.oauthToken = "already_registered"
            return await self.async_step_activate(user_input)

        return await self._show_config_form(user_input)

    def reason_for_error(self):
        for error_type, reason in (
            (HAVSCodeDownloadException, "download"),
            (HAVSCodeAuthenticationException, "authentication"),
            (HAVSCodeTarException, "zip"),
            (HAVSCodeZipException, "zip"),
        ):
            if isinstance(self._error, error_type):
                return reason
        return "unknown"

    async def async_step_activate(self, _user_input):
        if not self.devURL and not self._error:
            result = await self.device.activate(timeout=self.timeout)
            if not result:
                self._error = HAVSCodeAuthenticationException()
            else:
                self.devURL = result

        if self._error:
            await self.hass.async_add_executor_job(self.device.stopTunnel)
            reason = self.reason_for_error()
            self.log.debug("Reason activation error: " + reason)
            return self.async_abort(reason=reason)

        await self.hass.async_add_executor_job(self.device.stopTunnel)
        # create entry and finish.
        return self.async_create_entry(
            title="HA VSCode Tunnel",
            data={
                "token": self.oauthToken,
                "dev_url": self.devURL,
                "path": self.path,
                "timeout": self.timeout,
            },
            description_placeholders={
                "url": self.devURL,
            },
        )

    @callback
    def async_remove(self):
        """Clean up resources or tasks associated with the flow."""
        self.log.info("Cleaning up...")
        if self.device:
            self.hass.async_add_executor_job(self.device.stopTunnel)

    async def _show_config_form(self, user_input):
        """Show the configuration form to edit location data."""

        self.activate = True

        return self.async_show_form(
            step_id="user",
            data_schema=None,
            description_placeholders={
                "url": "https://github.com/login/device",
                "token": self.oauthToken,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return HAVSCodeOptionsFlowHandler()


class HAVSCodeOptionsFlowHandler(config_entries.OptionsFlow):
    """Config flow options handler."""

    def __init__(self):
        """Initialize options without accessing the framework-owned entry."""
        self.device = None
        self.path = None
        self.devURL = None
        self.oauthToken = None
        self.timeout = None
        if self.timeout is None:
            self.timeout = 7.0
        self.log = LOGGER
        self._reauth = False

    async def async_step_init(self, _user_input=None):
        entry_data = {**self.config_entry.data, **self.config_entry.options}
        self.path = entry_data.get("path")
        self.devURL = entry_data.get("dev_url")
        self.oauthToken = entry_data.get("token")
        self.timeout = entry_data.get("timeout", 7.0)
        if self.path is None:
            self.path = os.path.join(self.hass.config.path("custom_components"), DOMAIN)
            self.path = os.path.join(self.path, "bin")
            self.log.debug("bin directory located at: " + self.path)

        active = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        if active is not None and active.isRunning():
            self.devURL = active.devURL or self.devURL
            return await self.async_step_user()

        if self.device is None:
            # start a tunnel and see if an oauth token is generated. if it is, then we need to reauth.
            self.device = VSCodeDeviceAPI(self.path)
            try:
                await self.hass.async_add_executor_job(self.device.startTunnel)
            except OSError:
                return self.async_abort(reason="reauth_error")
            token = await self.device.getOAuthToken()
            if token is not None:
                self.oauthToken = token
                self.log.debug("Reauthorization is needed.")
                self._reauth = True
                # we'll have to stop the tunnel later...
            else:
                url = await self.device.getDevURL(self.timeout)
                if url is not None:
                    self.devURL = url
                await self.hass.async_add_executor_job(self.device.stopTunnel)

        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            _timeout = float(user_input.get("timeout"))
            if self.timeout != _timeout:
                return self.async_create_entry(
                    title="HA VSCode Tunnel",
                    data={
                        "token": self.oauthToken,
                        "dev_url": self.devURL,
                        "path": self.path,
                        "timeout": _timeout,
                    },
                )

            return self.async_abort(reason="no_reauth_needed")

        if self.config_entry is None:
            return self.async_abort(reason="not_setup")

        schema = {
            vol.Required("timeout", default=self.timeout): vol.All(
                vol.Coerce(float), vol.Range(min=1, max=120)
            ),
        }
        if self._reauth:
            return self.async_show_form(
                step_id="reauth",
                data_schema=None,
                description_placeholders={
                    "token": self.oauthToken,
                    "url": "https://github.com/login/device",
                },
            )
        else:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(schema),
                description_placeholders={
                    "url": self.devURL,
                },
            )

    async def async_step_reauth(self, user_input=None):
        if user_input is not None:
            url = await self.device.getDevURL(self.timeout)
            await self.hass.async_add_executor_job(self.device.stopTunnel)
            if url is None:
                return self.async_abort(reason="reauth_error")
            self.devURL = url
            return self.async_create_entry(
                title="HA VSCode Tunnel",
                data={
                    "token": self.oauthToken,
                    "dev_url": self.devURL,
                    "path": self.path,
                    "timeout": self.timeout,
                },
            )

        return self.async_abort(reason="reauth_error")

    @callback
    def async_remove(self):
        """Clean up resources or tasks associated with the flow."""
        if self.device is not None:
            self.hass.async_add_executor_job(self.device.stopTunnel)
            self.device = None
