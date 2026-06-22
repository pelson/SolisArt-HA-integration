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
    coordinator: SolisartCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([SolisartRefreshButton(coordinator, entry.entry_id)])


class SolisartRefreshButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "refresh"

    def __init__(self, coordinator: SolisartCoordinator, entry_id: str) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"solisart_refresh_{entry_id}"

    async def async_press(self) -> None:
        await self._coordinator.async_request_refresh()
