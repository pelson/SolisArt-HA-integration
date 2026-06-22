import xml.etree.ElementTree as ET
from dataclasses import dataclass

from .decoder import decode_payload


@dataclass(frozen=True)
class SnapshotResponse:
    statut: str
    appli: str | None
    values: dict[int, str]


def parse_snapshot_xml(xml_text: str) -> SnapshotResponse:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(f"malformed snapshot XML: {exc}") from exc
    if root.tag != "valeurs":
        raise ValueError(f"unexpected root element: {root.tag}")
    values: dict[int, str] = {}
    for child in root:
        if child.tag != "valeur":
            continue
        donnee = child.get("donnee")
        encoded = child.get("valeur")
        if donnee is None or encoded is None:
            continue
        try:
            donnee_id = int(donnee)
        except ValueError:
            continue
        try:
            values[donnee_id] = decode_payload(encoded)
        except ValueError:
            # A single bad payload should not nuke the whole snapshot.
            # Skip it; the client can flag this via diagnostics.
            continue
    return SnapshotResponse(
        statut=root.get("statut", ""),
        appli=root.get("appli"),
        values=values,
    )
