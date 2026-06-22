import re

from .model import SensorReading, Snapshot, ZoneState
from .xml_parser import SnapshotResponse

_T_RE = re.compile(r"^t_(\d+)$")
_FL_RE = re.compile(r"^fl_(\d+)$")
_RL_RE = re.compile(r"^rl_(\d+)$")
_ZONE_LABEL_RE = re.compile(r"^tlbl_(1[1-4])$")
_LEADING_NUM_RE = re.compile(r"^[-+]?\d+(?:\.\d+)?")

# Real-firmware relay encoding (verified against captured fixtures): the box
# returns French/English enum strings on the wire, not "0"/"1". "Dsc"
# (déconnecté) and similar sentinels mean the input is not present and yield
# no binary state.
_RELAY_ON = {"on", "marche"}
_RELAY_OFF = {"off", "arret", "arrêt"}


def _parse_number(text: str, lo: float, hi: float) -> float | None:
    """Pull the leading signed-decimal from a value like ``"26.7 dC"`` or
    ``"0.0 l mn"`` and return it if within the inclusive range. Sentinels
    like ``"Dsc"`` (probe disconnected) or ``"Off"`` (sensor disabled)
    return ``None`` — no leading number, no reading."""
    match = _LEADING_NUM_RE.match(text.strip())
    if match is None:
        return None
    try:
        value = float(match.group(0))
    except ValueError:
        return None
    if lo <= value <= hi:
        return value
    return None


def _parse_relay(text: str) -> bool | None:
    token = text.strip().lower()
    if token in _RELAY_ON:
        return True
    if token in _RELAY_OFF:
        return False
    return None


def build_snapshot(
    response: SnapshotResponse, id_to_symbol: dict[int, str]
) -> Snapshot:
    by_symbol: dict[str, str] = {}
    for donnee_id, value in response.values.items():
        symbol = id_to_symbol.get(donnee_id)
        if symbol is not None:
            by_symbol[symbol] = value

    serial = by_symbol.get("serial") or None

    sensors: dict[str, SensorReading] = {}
    for symbol, value in by_symbol.items():
        m = _T_RE.match(symbol)
        if m:
            temp = _parse_number(value, -50.0, 200.0)
            if temp is None:
                continue
            suffix = int(m.group(1))
            label = by_symbol.get(f"tlbl_{suffix:02d}", symbol)
            sensors[symbol] = SensorReading(
                code=symbol, label=label, value=temp, unit="°C"
            )
            continue
        m = _FL_RE.match(symbol)
        if m:
            flow = _parse_number(value, 0.0, 1000.0)
            if flow is None:
                continue
            suffix = int(m.group(1))
            label = by_symbol.get(f"fllbl_{suffix}", symbol)
            sensors[symbol] = SensorReading(
                code=symbol, label=label, value=flow, unit="L/min"
            )

    binary: dict[str, bool] = {}
    for symbol, value in by_symbol.items():
        if _RL_RE.match(symbol):
            state = _parse_relay(value)
            if state is not None:
                binary[symbol] = state

    zones: list[ZoneState] = []
    for symbol, value in by_symbol.items():
        m = _ZONE_LABEL_RE.match(symbol)
        if not m:
            continue
        zone_n = int(m.group(1))  # 11..14
        t_symbol = f"t_{zone_n}"
        current = (
            _parse_number(by_symbol[t_symbol], -50.0, 200.0)
            if t_symbol in by_symbol
            else None
        )
        zones.append(
            ZoneState(
                index=zone_n - 11,
                label=value,
                current_temp=current,
                target_temp=None,
                mode=None,
            )
        )
    zones.sort(key=lambda z: z.index)

    return Snapshot(
        serial=serial,
        sensors=sensors,
        binary=binary,
        zones=zones,
        raw=dict(by_symbol),
    )
