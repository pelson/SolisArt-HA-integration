from pathlib import Path

import pytest

from custom_components.solisart.api.xml_parser import (
    SnapshotResponse,
    parse_snapshot_xml,
)

FIXTURE = Path("tests/fixtures/lecture_valeurs_donnees.sample.xml").read_text()


def test_parse_status_and_app_version():
    resp = parse_snapshot_xml(FIXTURE)
    assert isinstance(resp, SnapshotResponse)
    assert resp.statut == "succes"
    assert resp.appli  # firmware version present, exact value not asserted


def test_parse_values_keyed_by_int_donnee_id():
    resp = parse_snapshot_xml(FIXTURE)
    assert 520 in resp.values  # tlbl_01 per the JS dict
    assert resp.values[520] == "T1 Capt Chaud 1"


def test_parse_handles_many_values():
    resp = parse_snapshot_xml(FIXTURE)
    assert len(resp.values) >= 500  # fixture has ~638 valeur entries


def test_parse_rejects_non_xml():
    with pytest.raises(ValueError):
        parse_snapshot_xml("not xml at all")
