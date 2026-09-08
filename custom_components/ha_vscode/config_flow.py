"""Explicit, bounded authentication sessions for the VS Code CLI."""

import asyncio
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later

from .const import DOMAIN, NAME
from .exceptions import HAVSCodeException
from .vscode_device import TunnelBusyError, VSCodeDeviceAPI

LOGGER = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 7.0
SESSION_SECONDS = 600


def timeout_schema(default=DEFAULT_TIMEOUT, options=False):
    schema = {
        vol.Required("timeout", default=default): vol.All(
            vol.Coerce(float), vol.Range(min=1, max=120)
        )
    }
    if options:
        schema[vol.Optional("check_auth", default=False)] = bool
    return vol.Schema(schema)


class AuthenticationSession:
    """Share state handling, own the probe, and always release it on exit."""

    def __init__(self):
        self.device = None
        self.timeout = DEFAULT_TIMEOUT
        self.path = None
        self._owner = object()
        self._claimed = False
        self._expired = False
        self._cancel_expiry = None
        self._cancel_shutdown = None

    async def _probe_job(self, function):
        # Cancelling an await does not stop a worker thread. Release ownership
        # after that worker finishes, even when the flow has already disappeared.
        job = asyncio.ensure_future(
            self.hass.async_add_executor_job(function, self._owner)
        )
        try:
            return await asyncio.shield(job)
        except asyncio.CancelledError:

            def release_when_done(done):
                if not done.cancelled():
                    done.exception()  # Retrieve errors without logging credentials.
                self.hass.async_add_executor_job(self.device.release_probe, self._owner)

            job.add_done_callback(release_when_done)
            self.async_remove()
            raise

    async def _begin(self):
        try:
            await self._probe_job(self.device.claim_probe)
            self._claimed = True
        except TunnelBusyError:
            return self.async_abort(reason="tunnel_busy")
        # Expiry covers abandoned browser dialogs as well as active retries.
        self._cancel_shutdown = self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, self._expire
        )
        self._cancel_expiry = async_call_later(self.hass, SESSION_SECONDS, self._expire)
        try:
            await self._probe_job(self.device.startTunnel)
        except (HAVSCodeException, OSError, TunnelBusyError):
            LOGGER.warning("Unable to install or start the tunnel CLI")
            await self._cleanup()
            return self.async_abort(reason="cannot_start")
        except asyncio.CancelledError:
            self.async_remove()
            raise
        return await self.async_step_wait()

    @callback
    def _expire(self, _now):
        self._expired = True
        self.async_remove()

    async def _cleanup(self):
        if self._cancel_shutdown is not None:
            self._cancel_shutdown()
            self._cancel_shutdown = None
        if self._cancel_expiry is not None:
            self._cancel_expiry()
            self._cancel_expiry = None
        if self._claimed:
            await self.hass.async_add_executor_job(
                self.device.release_probe, self._owner
            )
            self._claimed = False

    @callback
    def async_remove(self):
        if self._cancel_shutdown is not None:
            self._cancel_shutdown()
            self._cancel_shutdown = None
        if self._cancel_expiry is not None:
            self._cancel_expiry()
            self._cancel_expiry = None
        if self._claimed:
            self.hass.async_add_executor_job(self.device.release_probe, self._owner)
            self._claimed = False

    async def _observe(self, after_auth=False):
        if self._expired:
            return self.async_abort(reason="session_expired")
        state = await self.device.wait_status(self.timeout, after_auth=after_auth)
        if self._expired:
            return self.async_abort(reason="session_expired")
        if state == "ready":
            url = self.device.devURL
            await self._cleanup()
            return self._finish(url)
        if state == "stopped":
            LOGGER.warning(
                "Tunnel stopped before URL readiness (category=%s)",
                self.device.last_error or "unknown",
            )
            await self._cleanup()
            return self.async_abort(reason="tunnel_exited")
        if state == "auth_required":
            return self.async_show_form(
                step_id="authorize",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "url": "https://github.com/login/device",
                    "token": self.device.oauthToken,
                },
            )
        return self.async_show_form(step_id="wait", data_schema=vol.Schema({}))

    async def async_step_wait(self, user_input=None):
        return await self._observe()

    async def async_step_authorize(self, user_input=None):
        return await self._observe(after_auth=True)


class HAVSCodeFlowHandler(
    AuthenticationSession, config_entries.ConfigFlow, domain=DOMAIN
):
    """One tunnel integration per Home Assistant installation."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=timeout_schema())
        try:
            self.timeout = timeout_schema()(user_input)["timeout"]
        except vol.Invalid:
            return self.async_show_form(
                step_id="user",
                data_schema=timeout_schema(),
                errors={"base": "invalid_timeout"},
            )
        self.path = self.hass.config.path("custom_components", DOMAIN, "bin")
        self.device = VSCodeDeviceAPI(
            self.path,
            self.hass.config.path(".ha_vscode"),
            "homeassistant",
        )
        return await self._begin()

    def _finish(self, url):
        return self.async_create_entry(
            title=NAME,
            data={"path": self.path, "dev_url": url, "timeout": self.timeout},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HAVSCodeOptionsFlowHandler()


class HAVSCodeOptionsFlowHandler(AuthenticationSession, config_entries.OptionsFlow):
    """Opening settings has no subprocess or authentication side effects."""

    async def async_step_init(self, user_input=None):
        data = {**self.config_entry.data, **self.config_entry.options}
        self.path = data.get("path") or self.hass.config.path(
            "custom_components", DOMAIN, "bin"
        )
        self.timeout = data.get("timeout", DEFAULT_TIMEOUT)
        if user_input is None:
            return self.async_show_form(
                step_id="init", data_schema=timeout_schema(self.timeout, options=True)
            )
        try:
            values = timeout_schema(self.timeout, options=True)(user_input)
        except vol.Invalid:
            return self.async_show_form(
                step_id="init",
                data_schema=timeout_schema(self.timeout, options=True),
                errors={"base": "invalid_timeout"},
            )
        self.timeout = values["timeout"]
        if not values.get("check_auth"):
            return self._finish(None)
        self.device = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        if self.device is None:
            return self.async_abort(reason="not_loaded")
        return await self._begin()

    def _finish(self, url):
        options = {**self.config_entry.options, "timeout": self.timeout}
        options.pop("token", None)
        if url is not None:
            options["dev_url"] = url
        return self.async_create_entry(title="", data=options)
