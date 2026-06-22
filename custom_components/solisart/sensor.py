from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_EXPOSE_DIAGNOSTIC, DOMAIN
from .coordinator import SolisartCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SolisartCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    snap = coordinator.data
    entities: list[SensorEntity] = []
    seen: set[str] = set()
    for code, _reading in snap.sensors.items():
        entities.append(SolisartSensor(coordinator, code))
        seen.add(code)
    if entry.options.get(CONF_EXPOSE_DIAGNOSTIC, False):
        for code in snap.raw:
            if code in seen or code in snap.binary:
                continue
            entities.append(SolisartDiagnosticSensor(coordinator, code))
    async_add_entities(entities)


class SolisartSensor(CoordinatorEntity[SolisartCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: SolisartCoordinator, code: str) -> None:
        super().__init__(coordinator)
        self._code = code
        self._attr_unique_id = f"solisart_{code}"
        reading = coordinator.data.sensors[code]
        self._attr_name = reading.label
        self._attr_native_unit_of_measurement = reading.unit
        if reading.unit == "°C":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif reading.unit == "L/min":
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        reading = self.coordinator.data.sensors.get(self._code)
        return reading.value if reading is not None else None


class SolisartDiagnosticSensor(CoordinatorEntity[SolisartCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: SolisartCoordinator, code: str) -> None:
        super().__init__(coordinator)
        self._code = code
        self._attr_unique_id = f"solisart_diag_{code}"
        self._attr_name = code

    @property
    def native_value(self):
        return self.coordinator.data.raw.get(self._code)
