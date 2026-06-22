# Test fixtures

These are anonymised captures from a real SolisArt box (firmware/app
version `3.0.18`). Regenerate when the box firmware changes the protocol
(rare).

## Files

- `lecture_valeurs_donnees.sample.xml` — a snapshot of the box's live
  data values, captured from `POST /admin/divers/ajax/lecture_valeurs_donnees.php`.
  Each `<valeur>` element carries a numeric `donnee` code and a
  base64-encoded `valeur`. The numeric codes are mapped to symbolic
  names (`tlbl_*`, `fllbl_*`, `trilbl_*`, `rl_*`, etc.) via `const
  donnee_<name> = <code>;` declarations in the dict file below — the
  XML itself does not carry the symbolic names directly.
- `commun-donnees.sample.js` — the box's static label dictionary,
  served from `/admin/divers/js/solisart/commun-donnees.<hash>.js`.
  Maps numeric `donnee`/`attribut` codes to symbolic names and French
  display labels. This file is not instance-specific (no install ID,
  serial, or owner data) — it ships identically with the firmware.

## Regenerating

Set `SOLISART_TEST_HOST` / `_USER` / `_PASS` / `_INSTALL_ID` in
`secrets.env` (gitignored), then:

```bash
set -a; source secrets.env; set +a

COOKIE=$(mktemp)

# Log in
curl -s -c "$COOKIE" -b "$COOKIE" \
  -d "id=${SOLISART_TEST_USER}&pass=${SOLISART_TEST_PASS}&ihm=admin&connexion=1" \
  "http://${SOLISART_TEST_HOST}/" -o /dev/null

# Snapshot XML — needs base64-encoded install id, a starting "heure"
# timestamp (0 works for a full dump), and a "periode" in seconds.
ID_B64=$(echo -n "${SOLISART_TEST_INSTALL_ID}" | base64)
curl -s -b "$COOKIE" -X POST \
  -d "id=${ID_B64}&heure=$(echo -n 0 | base64)&periode=5" \
  "http://${SOLISART_TEST_HOST}/admin/divers/ajax/lecture_valeurs_donnees.php" \
  > tests/fixtures/lecture_valeurs_donnees.sample.xml

# Dict file — discover current hash from the installation page first
HASH=$(curl -s -b "$COOKIE" \
  "http://${SOLISART_TEST_HOST}/admin/index.php?page=installation&id=${SOLISART_TEST_INSTALL_ID}" \
  | grep -oE 'commun-donnees\.[a-f0-9]+\.js' | head -1)
curl -s -b "$COOKIE" \
  "http://${SOLISART_TEST_HOST}/admin/divers/js/solisart/${HASH}" \
  > tests/fixtures/commun-donnees.sample.js
```

## Anonymisation checklist (do this before every commit)

The XML snapshot contains base64-encoded values — decode each
`donnee`/`valeur` pair and inspect it before committing. At minimum,
redact (replace the underlying plaintext with `XXXX` or `0`, then
re-encode to base64):

- `donnee="3"` — installation ID (a short alphanumeric box identifier)
- `donnee="4"` — installation label / owner name
- `donnee="499"` — MAC address (`donnee_config_mac` in the dict)
- `donnee="508"`..`"515"` — gateway/DNS IP address octets
- `donnee="1"` — vendor management hostname (defensive redaction)

Do **not** decode the rest of the file — the decoder is implemented
and tested separately (see `test_decoder.py`). Leave temperatures,
flow rates, valve/relay enum strings, and French labels as-is; they
are not PII.

The dict file (`commun-donnees.sample.js`) is a static firmware asset
and has not been found to contain instance-specific data, but
re-check with a PII grep before committing if it changes shape.
