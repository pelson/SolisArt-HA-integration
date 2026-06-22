import base64
import binascii


def decode_payload(blob: str) -> str:
    """Decode a single base64-encoded value from the lecture_valeurs_donnees XML.

    The SolisArt box returns each <valeur valeur="…"/> attribute as a plain
    base64 string. No HTML entity escaping is applied on current firmware.
    """
    try:
        return base64.b64decode(blob.strip(), validate=True).decode("utf-8")
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"invalid base64 payload: {exc}") from exc
