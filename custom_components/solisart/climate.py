from __future__ import annotations

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
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
    zones = coordinator.data.zones
    async_add_entities(SolisartZone(coordinator, z.index, device_info) for z in zones)


class SolisartZone(CoordinatorEntity[SolisartCoordinator], ClimateEntity):
    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature(0)  # read-only in v0.1
    _attr_hvac_modes = [HVACMode.AUTO]

    def __init__(self, coordinator: SolisartCoordinator, index: int, device_info) -> None:
        super().__init__(coordinator)
        self._index = index
        self._attr_unique_id = f"solisart_zone_{index}"
        self._attr_device_info = device_info
        zone = self._zone()
        self._attr_name = zone.label if zone else f"Zone {index}"

    def _zone(self):
        for z in self.coordinator.data.zones:
            if z.index == self._index:
                return z
        return None

    @property
    def current_temperature(self) -> float | None:
        z = self._zone()
        return z.current_temp if z else None

    @property
    def target_temperature(self) -> float | None:
        z = self._zone()
        return z.target_temp if z else None

    @property
    def hvac_mode(self) -> HVACMode:
        return HVACMode.AUTO
