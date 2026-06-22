import base64
import re
from pathlib import Path

import pytest

from custom_components.solisart.api.decoder import decode_payload


def test_decode_plain_ascii():
    assert decode_payload(base64.b64encode(b"42.5").decode()) == "42.5"


def test_decode_utf8_with_special_chars():
    plain = "T1 Capt Chaud 1"
    assert decode_payload(base64.b64encode(plain.encode("utf-8")).decode()) == plain


def test_decode_strips_whitespace():
    plain = "0"
    b64 = base64.b64encode(plain.encode()).decode()
    assert decode_payload(f"  {b64}  ") == plain


def test_decode_invalid_base64_raises():
    with pytest.raises(ValueError):
        decode_payload("not!valid@base64")


def test_decode_real_fixture_label():
    raw = Path("tests/fixtures/lecture_valeurs_donnees.sample.xml").read_text()
    m = re.search(r'<valeur[^/]*donnee="520"[^/]*valeur="([^"]+)"', raw)
    assert m, "fixture missing donnee=520 (tlbl_01)"
    assert decode_payload(m.group(1)) == "T1 Capt Chaud 1"
