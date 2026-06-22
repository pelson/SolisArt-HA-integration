"""Minimal homeassistant stubs so the dev venv can import the package."""
from __future__ import annotations

import sys
import types
from enum import StrEnum

# ---------------------------------------------------------------------------
# homeassistant.const – Platform enum
# ---------------------------------------------------------------------------

class Platform(StrEnum):
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    CLIMATE = "climate"
    BUTTON = "button"
    NUMBER = "number"
    SELECT = "select"
    SWITCH = "switch"


# ---------------------------------------------------------------------------
# homeassistant.core – HomeAssistant placeholder
# ---------------------------------------------------------------------------

class HomeAssistant:
    """Stub for type-checking and subclass use."""


# ---------------------------------------------------------------------------
# homeassistant.config_entries – ConfigEntry placeholder
# ---------------------------------------------------------------------------

class ConfigEntry:
    """Stub for type-checking."""


# ---------------------------------------------------------------------------
# homeassistant.helpers.update_coordinator stubs
# ---------------------------------------------------------------------------

class UpdateFailed(Exception):
    """Signal a failed update."""


class DataUpdateCoordinator:
    """Minimal stub so SolisartCoordinator can subclass it."""

    def __init__(self, hass, *, logger, name, update_interval=None, **kwargs):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data = None

    def __class_getitem__(cls, item):
        return cls


# ---------------------------------------------------------------------------
# Wire everything into sys.modules before any custom_components import runs
# ---------------------------------------------------------------------------

def _make_module(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


_ha = _make_module("homeassistant")
_ha_const = _make_module("homeassistant.const", Platform=Platform)
_ha_core = _make_module("homeassistant.core", HomeAssistant=HomeAssistant)
_ha_ce = _make_module("homeassistant.config_entries", ConfigEntry=ConfigEntry)
_ha_helpers = _make_module("homeassistant.helpers")
_ha_uc = _make_module(
    "homeassistant.helpers.update_coordinator",
    DataUpdateCoordinator=DataUpdateCoordinator,
    UpdateFailed=UpdateFailed,
)


class DeviceInfo(dict):
    """Stub matching HA's TypedDict-style DeviceInfo."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)


_ha_dr = _make_module(
    "homeassistant.helpers.device_registry",
    DeviceInfo=DeviceInfo,
)
