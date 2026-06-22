from dataclasses import dataclass, field


@dataclass(frozen=True)
class SensorReading:
    code: str
    label: str
    value: float | str
    unit: str | None = None


@dataclass(frozen=True)
class ZoneState:
    index: int
    label: str
    current_temp: float | None
    target_temp: float | None
    mode: str | None


@dataclass(frozen=True)
class Snapshot:
    serial: str | None
    sensors: dict[str, SensorReading] = field(default_factory=dict)
    binary: dict[str, bool] = field(default_factory=dict)
    zones: list[ZoneState] = field(default_factory=list)
    raw: dict[str, str] = field(default_factory=dict)
