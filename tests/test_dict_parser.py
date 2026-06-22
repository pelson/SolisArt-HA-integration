from pathlib import Path

from custom_components.solisart.api.dict_parser import parse_donnee_dict

FIXTURE = Path("tests/fixtures/commun-donnees.sample.js").read_text()


def test_parse_returns_id_to_symbol_map():
    d = parse_donnee_dict(FIXTURE)
    assert d[520] == "tlbl_01"
    assert d[532] == "fllbl_1"
    assert d[60] == "tlbl_11"
    assert d[606] == "rl_0"

def test_skips_commented_declarations():
    # In the fixture, donnee_rl_1 (id 607) is commented out — unsupported
    # on this firmware. It must not appear in the parsed map.
    d = parse_donnee_dict(FIXTURE)
    assert 607 not in d

def test_covers_temperature_value_codes():
    # tr_1..tr_13 live at 614..626; tr_14..tr_26 at 1742..1754.
    d = parse_donnee_dict(FIXTURE)
    assert d[614] == "tr_1"
    assert d[1742] == "tr_14"

def test_dict_is_large():
    d = parse_donnee_dict(FIXTURE)
    assert len(d) >= 1000  # the captured fixture has ~1372 entries

def test_parse_synthetic_minimal_input():
    src = """
        // header
        const donnee_serial = 3;
        //const donnee_rl_1 = 607;
        const donnee_tlbl_01 = 520;
        const version_application = "3.0.13";
    """
    d = parse_donnee_dict(src)
    assert d == {3: "serial", 520: "tlbl_01"}
