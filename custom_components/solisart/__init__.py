from __future__ import annotations

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .api.client import SolisartClient, make_session
from .api.endpoint import EndpointStrategy
from .const import (
    CONF_CLOUD_URL,
    CONF_INSTALL_ID,
    CONF_LOCAL_URL,
    CONF_MODE,
    CONF_PASSWORD_CLOUD,
    CONF_PASSWORD_LOCAL,
    CONF_UPDATE_INTERVAL_MIN,
    CONF_UPDATE_MODE,
    CONF_USERNAME_CLOUD,
    CONF_USERNAME_LOCAL,
    DEFAULT_TIMER_INTERVAL_MIN,
    DOMAIN,
    MODE_CLOUD,
    MODE_LOCAL,
    UPDATE_MODE_TIMER,
)
from .coordinator import SolisartCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.BUTTON,
]


def _client_from_entry(
    session: aiohttp.ClientSession, data: dict
) -> SolisartClient:
    mode = data[CONF_MODE]
    endpoint = EndpointStrategy(
        mode=mode,
        local_url=data.get(CONF_LOCAL_URL),
        cloud_url=data.get(CONF_CLOUD_URL),
    )
    if mode == MODE_CLOUD:
        username = data[CONF_USERNAME_CLOUD]
        password = data[CONF_PASSWORD_CLOUD]
    elif mode == MODE_LOCAL:
        username = data[CONF_USERNAME_LOCAL]
        password = data[CONF_PASSWORD_LOCAL]
    else:
        # fallback: prefer local creds; cloud creds tried only if local fails
        username = data.get(CONF_USERNAME_LOCAL) or data[CONF_USERNAME_CLOUD]
        password = data.get(CONF_PASSWORD_LOCAL) or data[CONF_PASSWORD_CLOUD]
    return SolisartClient(
        session=session,
        endpoint=endpoint,
        username=username,
        password=password,
        install_id=data.get(CONF_INSTALL_ID),
    )


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    data = {**entry.data, **entry.options}
    mode = data.get(CONF_MODE)
    if mode == MODE_CLOUD:
        url = data.get(CONF_CLOUD_URL)
    else:
        url = data.get(CONF_LOCAL_URL) or data.get(CONF_CLOUD_URL)
    install_id = data.get(CONF_INSTALL_ID) or entry.entry_id
    return DeviceInfo(
        identifiers={(DOMAIN, install_id)},
        name="SolisArt",
        manufacturer="SolisArt",
        model="SolisArt box",
        configuration_url=url,
        serial_number=data.get(CONF_INSTALL_ID),
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = make_session()
    client = _client_from_entry(session, {**entry.data, **entry.options})
    coordinator = SolisartCoordinator(
        hass,
        client,
        update_mode=entry.options.get(CONF_UPDATE_MODE, entry.data.get(CONF_UPDATE_MODE)),
        interval_min=entry.options.get(
            CONF_UPDATE_INTERVAL_MIN,
            entry.data.get(CONF_UPDATE_INTERVAL_MIN, DEFAULT_TIMER_INTERVAL_MIN),
        ),
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
        "session": session,
        "device_info": _device_info(entry),
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if entry.version < 2:
        new_options = dict(entry.options)
        if new_options.get(CONF_UPDATE_MODE) in ("slow", "fast"):
            new_options[CONF_UPDATE_MODE] = UPDATE_MODE_TIMER
        hass.config_entries.async_update_entry(entry, options=new_options, version=2)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    bucket = hass.data[DOMAIN].pop(entry.entry_id, None) if ok else None
    if bucket is not None:
        session: aiohttp.ClientSession = bucket["session"]
        await session.close()
    return ok


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
