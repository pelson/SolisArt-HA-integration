from custom_components.solisart.api.model import (
    SensorReading,
    Snapshot,
    ZoneState,
)


def test_sensor_reading_is_frozen():
    r = SensorReading(code="tlbl_01", label="Capt chaud", value=42.5, unit="°C")
    try:
        r.value = 0
    except Exception:
        return
    raise AssertionError("SensorReading should be frozen")

def test_snapshot_holds_typed_collections():
    snap = Snapshot(
        serial="XXXX",
        sensors={"tlbl_01": SensorReading("tlbl_01", "Capt chaud", 42.5, "°C")},
        binary={"rl_pompe_1": True},
        zones=[ZoneState(index=0, label="Zone 1", current_temp=20.5,
                         target_temp=21.0, mode="heat")],
        raw={"tlbl_01": "42.5"},
    )
    assert snap.sensors["tlbl_01"].value == 42.5
    assert snap.binary["rl_pompe_1"] is True
    assert snap.zones[0].current_temp == 20.5
