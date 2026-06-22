import re

from .model import SensorReading, Snapshot, ZoneState
from .xml_parser import SnapshotResponse

_TR_RE = re.compile(r"^tr_(\d+)$")
_RL_RE = re.compile(r"^rl_(\d+)$")
_TLBL_RE = re.compile(r"^tlbl_(\d{2})$")
_ZONE_LABEL_RE = re.compile(r"^tlbl_(1[1-4])$")


def _parse_temperature(text: str) -> float | None:
    # Box values are decimal strings; some come with a trailing unit like
    # " dC" or " l mn". Strip non-numeric suffixes before parsing.
    head = text.strip().split(" ", 1)[0]
    try:
        v = float(head)
    except ValueError:
        return None
    if -50.0 <= v <= 200.0:
        return v
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
        m = _TR_RE.match(symbol)
        if not m:
            continue
        temp = _parse_temperature(value)
        if temp is None:
            continue
        suffix = int(m.group(1))
        label = by_symbol.get(f"tlbl_{suffix:02d}", symbol)
        sensors[symbol] = SensorReading(
            code=symbol, label=label, value=temp, unit="°C"
        )

    binary: dict[str, bool] = {}
    for symbol, value in by_symbol.items():
        if _RL_RE.match(symbol) and value.strip() in ("0", "1"):
            binary[symbol] = value.strip() == "1"

    zones: list[ZoneState] = []
    for symbol, value in by_symbol.items():
        m = _ZONE_LABEL_RE.match(symbol)
        if not m:
            continue
        zone_n = int(m.group(1))  # 11..14
        tr_symbol = f"tr_{zone_n}"
        current = (
            _parse_temperature(by_symbol[tr_symbol])
            if tr_symbol in by_symbol
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
