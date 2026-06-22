from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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
    async_add_entities(
        SolisartBinary(coordinator, code, device_info) for code in coordinator.data.binary
    )


class SolisartBinary(CoordinatorEntity[SolisartCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: SolisartCoordinator, code: str, device_info) -> None:
        super().__init__(coordinator)
        self._code = code
        self._attr_unique_id = f"solisart_{code}"
        self._attr_name = code
        self._attr_device_info = device_info

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.binary.get(self._code)
