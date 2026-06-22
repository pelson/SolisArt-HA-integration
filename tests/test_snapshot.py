from pathlib import Path

from custom_components.solisart.api.dict_parser import parse_donnee_dict
from custom_components.solisart.api.snapshot import build_snapshot
from custom_components.solisart.api.xml_parser import SnapshotResponse, parse_snapshot_xml

# Synthetic id↔symbol mapping mirroring real-box semantics. Temperature
# measurements live under the `t_N` family on production firmware
# (e.g. "26.7 dC"); `tr_N` carries something else (`"0pC"` percentages —
# possibly modulation duty cycle) and is intentionally not modelled here.
ID_TO_SYMBOL = {
    3: "serial",
    520: "tlbl_01",      # label for temperature sensor 1
    532: "fllbl_1",      # label for flow sensor 1
    60:  "tlbl_11",      # label for zone 1
    520_001: "t_1",      # synthetic ids — irrelevant, only symbol matters
    520_011: "t_11",
    540_001: "fl_1",
    606: "rl_0",
}


def _resp(values: dict[int, str]) -> SnapshotResponse:
    return SnapshotResponse(statut="succes", appli="3.0.18", values=values)


def test_temperature_uses_tlbl_friendly_name():
    snap = build_snapshot(
        _resp({520: "Capt chaud 1", 520_001: "42.5 dC"}), ID_TO_SYMBOL
    )
    assert snap.sensors["t_1"].value == 42.5
    assert snap.sensors["t_1"].unit == "°C"
    assert snap.sensors["t_1"].label == "Capt chaud 1"


def test_temperature_without_label_falls_back_to_symbol():
    snap = build_snapshot(_resp({520_001: "20.0 dC"}), ID_TO_SYMBOL)
    assert snap.sensors["t_1"].value == 20.0
    assert snap.sensors["t_1"].label == "t_1"


def test_disconnected_probe_yields_no_sensor():
    snap = build_snapshot(_resp({520_001: "Dsc"}), ID_TO_SYMBOL)
    assert "t_1" not in snap.sensors


def test_flow_reading_uses_fllbl_label_and_l_per_min():
    snap = build_snapshot(
        _resp({532: "Débit principal", 540_001: "3.2 l mn"}), ID_TO_SYMBOL
    )
    assert snap.sensors["fl_1"].value == 3.2
    assert snap.sensors["fl_1"].unit == "L/min"
    assert snap.sensors["fl_1"].label == "Débit principal"


def test_flow_off_sentinel_yields_no_sensor():
    snap = build_snapshot(_resp({540_001: "Off"}), ID_TO_SYMBOL)
    assert "fl_1" not in snap.sensors


def test_relay_on_string_is_true():
    snap = build_snapshot(_resp({606: "On"}), ID_TO_SYMBOL)
    assert snap.binary["rl_0"] is True


def test_relay_off_string_is_false():
    snap = build_snapshot(_resp({606: "Off"}), ID_TO_SYMBOL)
    assert snap.binary["rl_0"] is False


def test_relay_french_marche_arret_supported():
    snap = build_snapshot(_resp({606: "Marche"}), ID_TO_SYMBOL)
    assert snap.binary["rl_0"] is True


def test_relay_unknown_value_skipped():
    snap = build_snapshot(_resp({606: "?"}), ID_TO_SYMBOL)
    assert "rl_0" not in snap.binary


def test_zone_built_from_tlbl_11_and_t_11():
    snap = build_snapshot(
        _resp({60: "Salon", 520_011: "20.5 dC"}), ID_TO_SYMBOL
    )
    assert len(snap.zones) == 1
    assert snap.zones[0].index == 0
    assert snap.zones[0].label == "Salon"
    assert snap.zones[0].current_temp == 20.5


def test_zone_without_temperature_still_emitted():
    snap = build_snapshot(_resp({60: "Salon"}), ID_TO_SYMBOL)
    assert len(snap.zones) == 1
    assert snap.zones[0].current_temp is None


def test_serial_extracted():
    snap = build_snapshot(_resp({3: "SC1Z00000000"}), ID_TO_SYMBOL)
    assert snap.serial == "SC1Z00000000"


def test_temperature_out_of_range_skipped():
    snap = build_snapshot(_resp({520_001: "9999 dC"}), ID_TO_SYMBOL)
    assert "t_1" not in snap.sensors


def test_unknown_donnee_ids_ignored():
    snap = build_snapshot(_resp({9999: "mystery"}), ID_TO_SYMBOL)
    assert "mystery" not in snap.raw.values()


def test_real_fixture_populates_snapshot():
    xml = Path("tests/fixtures/lecture_valeurs_donnees.sample.xml").read_text()
    js = Path("tests/fixtures/commun-donnees.sample.js").read_text()
    snap = build_snapshot(parse_snapshot_xml(xml), parse_donnee_dict(js))
    # Several t_N probes are connected on this fixture (t_2, t_3, t_4, t_7,
    # t_8, t_9, t_11, t_12) — confirm at least one parsed as a temperature.
    temps = [r for r in snap.sensors.values() if r.unit == "°C"]
    assert len(temps) >= 3, f"expected ≥3 temperature readings, got {len(temps)}"
    # The label for t_2 should come from tlbl_02.
    assert "t_2" in snap.sensors
    assert snap.sensors["t_2"].label.startswith("T2")
    # rl_0 = "Off" → False on real firmware.
    assert snap.binary.get("rl_0") is False
    # Four zones, derived from tlbl_11..14.
    assert len(snap.zones) == 4
    assert snap.zones[0].label.startswith("T11")
