from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api.client import (
    SolisartAuthError,
    SolisartClient,
    SolisartConnectionError,
    make_session,
)
from .api.endpoint import EndpointStrategy
from .const import (
    CONF_CLOUD_URL,
    CONF_EXPOSE_DIAGNOSTIC,
    CONF_INSTALL_ID,
    CONF_LOCAL_URL,
    CONF_MODE,
    CONF_PASSWORD_CLOUD,
    CONF_PASSWORD_LOCAL,
    CONF_UPDATE_INTERVAL_MIN,
    CONF_UPDATE_MODE,
    CONF_USERNAME_CLOUD,
    CONF_USERNAME_LOCAL,
    DEFAULT_CLOUD_URL,
    DEFAULT_SLOW_INTERVAL_MIN,
    DEFAULT_UPDATE_MODE,
    DOMAIN,
    MODE_CLOUD,
    MODE_FALLBACK,
    MODE_LOCAL,
    UPDATE_MODE_FAST,
    UPDATE_MODE_MANUAL,
    UPDATE_MODE_SLOW,
)

_MODE_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[MODE_LOCAL, MODE_CLOUD, MODE_FALLBACK],
        mode=SelectSelectorMode.DROPDOWN,
        translation_key="mode",
    )
)

_UPDATE_MODE_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[UPDATE_MODE_MANUAL, UPDATE_MODE_SLOW, UPDATE_MODE_FAST],
        mode=SelectSelectorMode.DROPDOWN,
        translation_key="update_mode",
    )
)


async def _validate(hass, data: dict) -> dict[str, str]:
    """Return {} on success or a single-entry error dict on failure."""
    mode = data[CONF_MODE]
    endpoint = EndpointStrategy(
        mode=mode,
        local_url=data.get(CONF_LOCAL_URL),
        cloud_url=data.get(CONF_CLOUD_URL),
    )
    if mode == MODE_LOCAL:
        user, pw = data[CONF_USERNAME_LOCAL], data[CONF_PASSWORD_LOCAL]
    elif mode == MODE_CLOUD:
        user, pw = data[CONF_USERNAME_CLOUD], data[CONF_PASSWORD_CLOUD]
    else:
        user = data.get(CONF_USERNAME_LOCAL) or data[CONF_USERNAME_CLOUD]
        pw = data.get(CONF_PASSWORD_LOCAL) or data[CONF_PASSWORD_CLOUD]
    async with make_session() as session:
        client = SolisartClient(session, endpoint, user, pw, data.get(CONF_INSTALL_ID))
        try:
            await client.login()
        except SolisartAuthError:
            return {"base": "invalid_auth"}
        except SolisartConnectionError:
            return {"base": "cannot_connect"}
        if mode == MODE_LOCAL and client.install_id is None:
            return {"base": "cannot_resolve_install_id"}
        data[CONF_INSTALL_ID] = client.install_id or data.get(CONF_INSTALL_ID)
        return {}


class SolisartConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input=None) -> FlowResult:
        return await self.async_step_endpoint(user_input)

    async def async_step_endpoint(self, user_input=None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            mode = user_input[CONF_MODE]
            if mode in (MODE_LOCAL, MODE_FALLBACK):
                return await self.async_step_credentials_local()
            return await self.async_step_credentials_cloud()
        schema = vol.Schema({
            vol.Required(CONF_MODE, default=MODE_LOCAL): _MODE_SELECTOR,
            vol.Optional(CONF_LOCAL_URL): str,
            vol.Optional(CONF_CLOUD_URL, default=DEFAULT_CLOUD_URL): str,
        })
        return self.async_show_form(step_id="endpoint", data_schema=schema)

    async def async_step_credentials_local(self, user_input=None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            if self._data[CONF_MODE] == MODE_FALLBACK:
                return await self.async_step_credentials_cloud()
            return await self._finalise()
        schema = vol.Schema({
            vol.Required(CONF_USERNAME_LOCAL): str,
            vol.Required(CONF_PASSWORD_LOCAL): str,
        })
        return self.async_show_form(step_id="credentials_local", data_schema=schema)

    async def async_step_credentials_cloud(self, user_input=None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return await self._finalise()
        schema = vol.Schema({
            vol.Required(CONF_USERNAME_CLOUD): str,
            vol.Required(CONF_PASSWORD_CLOUD): str,
            vol.Required(CONF_INSTALL_ID): str,
        })
        return self.async_show_form(step_id="credentials_cloud", data_schema=schema)

    async def _finalise(self) -> FlowResult:
        errors = await _validate(self.hass, self._data)
        if errors:
            return self.async_show_form(
                step_id="endpoint",
                data_schema=vol.Schema({
                    vol.Required(CONF_MODE, default=self._data[CONF_MODE]): _MODE_SELECTOR,
                    vol.Optional(CONF_LOCAL_URL, default=self._data.get(CONF_LOCAL_URL, "")): str,
                    vol.Optional(
                        CONF_CLOUD_URL,
                        default=self._data.get(CONF_CLOUD_URL, DEFAULT_CLOUD_URL),
                    ): str,
                }),
                errors=errors,
            )
        return await self.async_step_behavior()

    async def async_step_behavior(self, user_input=None) -> FlowResult:
        if user_input is not None:
            await self.async_set_unique_id(self._data.get(CONF_INSTALL_ID) or "solisart")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="SolisArt",
                data=self._data,
                options=user_input,
            )
        schema = vol.Schema({
            vol.Required(CONF_UPDATE_MODE, default=DEFAULT_UPDATE_MODE): _UPDATE_MODE_SELECTOR,
            vol.Optional(CONF_UPDATE_INTERVAL_MIN, default=DEFAULT_SLOW_INTERVAL_MIN): int,
            vol.Required(CONF_EXPOSE_DIAGNOSTIC, default=False): bool,
        })
        return self.async_show_form(step_id="behavior", data_schema=schema)

    async def async_step_reauth(self, entry_data) -> FlowResult:
        self._data = dict(entry_data)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None) -> FlowResult:
        if user_input is not None:
            self._data.update(user_input)
            errors = await _validate(self.hass, self._data)
            if errors:
                return self.async_show_form(
                    step_id="reauth_confirm",
                    data_schema=self._reauth_schema(),
                    errors=errors,
                )
            existing = self._get_reauth_entry()
            self.hass.config_entries.async_update_entry(existing, data=self._data)
            await self.hass.config_entries.async_reload(existing.entry_id)
            return self.async_abort(reason="reauth_successful")
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self._reauth_schema(),
        )

    def _reauth_schema(self) -> vol.Schema:
        mode = self._data.get(CONF_MODE, MODE_LOCAL)
        if mode == MODE_CLOUD:
            return vol.Schema({
                vol.Required(CONF_USERNAME_CLOUD): str,
                vol.Required(CONF_PASSWORD_CLOUD): str,
            })
        return vol.Schema({
            vol.Required(CONF_USERNAME_LOCAL): str,
            vol.Required(CONF_PASSWORD_LOCAL): str,
        })

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return SolisartOptionsFlow(entry)


class SolisartOptionsFlow(OptionsFlow):
    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        opts = self._entry.options
        schema = vol.Schema({
            vol.Required(
                CONF_UPDATE_MODE,
                default=opts.get(CONF_UPDATE_MODE, DEFAULT_UPDATE_MODE),
            ): _UPDATE_MODE_SELECTOR,
            vol.Optional(
                CONF_UPDATE_INTERVAL_MIN,
                default=opts.get(CONF_UPDATE_INTERVAL_MIN, DEFAULT_SLOW_INTERVAL_MIN),
            ): int,
            vol.Required(
                CONF_EXPOSE_DIAGNOSTIC,
                default=opts.get(CONF_EXPOSE_DIAGNOSTIC, False),
            ): bool,
        })
        return self.async_show_form(step_id="init", data_schema=schema)
