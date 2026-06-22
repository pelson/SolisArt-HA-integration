from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_INSTALL_ID,
    CONF_PASSWORD_CLOUD,
    CONF_PASSWORD_LOCAL,
    CONF_USERNAME_CLOUD,
    CONF_USERNAME_LOCAL,
    DOMAIN,
)

TO_REDACT = {
    CONF_PASSWORD_LOCAL,
    CONF_PASSWORD_CLOUD,
    CONF_USERNAME_LOCAL,
    CONF_USERNAME_CLOUD,
    CONF_INSTALL_ID,
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    bucket = hass.data[DOMAIN].get(entry.entry_id, {})
    coordinator = bucket.get("coordinator")
    snap = coordinator.data if coordinator is not None else None
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "snapshot": {
            "serial": "REDACTED" if snap and snap.serial else None,
            "raw": dict(snap.raw) if snap else {},
            "sensors": (
                {k: r.value for k, r in snap.sensors.items()} if snap else {}
            ),
            "binary": dict(snap.binary) if snap else {},
        },
        "last_update_success": (
            coordinator.last_update_success if coordinator is not None else None
        ),
        "last_exception": (
            str(coordinator.last_exception)
            if coordinator is not None and coordinator.last_exception is not None
            else None
        ),
    }
