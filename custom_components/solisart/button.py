from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SolisartCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    bucket = hass.data[DOMAIN][entry.entry_id]
    coordinator: SolisartCoordinator = bucket["coordinator"]
    device_info = bucket["device_info"]
    async_add_entities([SolisartRefreshButton(coordinator, entry.entry_id, device_info)])


class SolisartRefreshButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "refresh"

    def __init__(self, coordinator: SolisartCoordinator, entry_id: str, device_info) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"solisart_refresh_{entry_id}"
        self._attr_device_info = device_info

    async def async_press(self) -> None:
        await self._coordinator.async_request_refresh()
