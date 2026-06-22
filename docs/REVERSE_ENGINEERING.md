# SolisArt Protocol — Reverse Engineering Notes

## Why this file exists

The design spec (`docs/specs/2026-06-22-solisart-ha-integration-design.md`) was
written before live boxes were captured. Testing against two real installations
in June 2026 (firmware versions 3.0.13 and 3.0.18) revealed several places
where the spec's assumed protocol did not match the actual wire format. This
document records what was observed on those boxes. Where it conflicts with the
design spec, this document is correct. The implementation plan
(`docs/specs/2026-06-22-solisart-ha-v0.1-plan.md`) was updated to match these
findings; the design spec itself was not revised.

---

## Authentication

Login is a plain HTML form POST to the box root:

```
POST http://<box-ip>/
Content-Type: application/x-www-form-urlencoded

id=<username>&pass=<password>&ihm=admin&connexion=1
```

A successful login returns HTTP 302 to `/admin/`. Success cannot be determined
from the status code alone — a failed login also returns 302 (or 200 with the
form re-rendered). The only reliable indicator is to follow the redirect and
check the resulting HTML: if `name="pass"` appears in the page, the login form
was re-rendered and authentication failed.

The session is carried by a `PHPSESSID` cookie. When using `aiohttp`, the
cookie jar must be constructed with `unsafe=True` to allow cookies to be sent
for plain IP-address hosts (aiohttp rejects cookies for bare IPs by default):

```python
jar = aiohttp.CookieJar(unsafe=True)
session = aiohttp.ClientSession(cookie_jar=jar)
```

---

## Discovering the install ID

The install ID is a short alphanumeric string (e.g. `SCxx00000000`). It is
embedded in link hrefs on the post-login landing page. Extract it with:

```
[?&]id=([A-Za-z0-9_-]+)
```

applied to any `<a href="...">` on `/admin/`. The pattern matches query
parameters like `?page=installation&id=<INSTALL_ID>`.

---

## The label dictionary file

The box serves a static firmware asset at:

```
/admin/divers/js/solisart/commun-donnees.<hash>.js
```

The `<hash>` is a numeric cache-buster (e.g. `1681381933`, a Unix timestamp).
Discover the current filename from the `<script src="...">` tag on the
`/admin/` landing page:

```bash
curl -s -b "$COOKIE" "http://<box-ip>/admin/" \
  | grep -oE 'commun-donnees\.[0-9]+\.js' | head -1
```

The file contains approximately 1370 active `const donnee_<symbol> = <id>;`
declarations, one per line. Lines beginning with `//const donnee_*` are
commented-out declarations: the code is defined in the firmware source but
disabled for this firmware build (e.g. unsupported hardware options). These
lines must be skipped.

The pattern to parse an active declaration:

```
^\s*const\s+donnee_([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\d+)\s*;
```

Non-`donnee_` constants (e.g. `const version_application = "3.0.13";`) are
present in some firmware builds and should be silently ignored by a parser
that only matches the `donnee_` prefix.

The file is a firmware asset, not installation-specific: it contains no install
ID, serial number, or owner data.

---

## The snapshot endpoint

Fetch a full data snapshot with:

```
POST http://<box-ip>/admin/divers/ajax/lecture_valeurs_donnees.php
Content-Type: application/x-www-form-urlencoded

id=<base64(install_id)>&heure=0&periode=5
```

Three fields are required:

- `id` — the install ID, base64-encoded.
- `heure` — a starting timestamp in seconds (integer or base64-encoded `"0"`
  both work; use plain `0` to request a full dump).
- `periode` — polling window in seconds, plain integer. **This field must NOT
  be base64-encoded.** Sending `base64("5")` returns `statut="echec"` with
  the message "Le format de la periode de l'envoi rapide est incorrect".

A bare POST with no body returns `statut="echec"` with "L'identifiant de
l'installation est absent de la requete".

The design spec described a simpler request body without these three fields.
This was incorrect on both tested firmware versions.

---

## Response format

A successful response:

```xml
<valeurs statut="succes" appli="3.0.18">
  <valeur heure="..." donnee="520" valeur="VDEgQ2FwdCBDaGF1ZCAx"/>
  <valeur heure="..." donnee="614" valeur="MjYuNyBkQw=="/>
  ...
</valeurs>
```

Each `<valeur>` carries:

- `donnee` — a numeric ID (integer, 1..~1820 depending on configuration).
- `valeur` — the value, encoded as plain base64.

The numeric `donnee` IDs are resolved to symbolic names by looking them up in
the dict file's `const donnee_<symbol> = <id>;` table. The XML itself does not
carry symbolic names.

On error:

```xml
<valeurs statut="echec">
  <message>...</message>
</valeurs>
```

The `<message>` text is a French-language explanation string.

---

## Value encoding

Each `valeur` attribute is a single base64-encoded UTF-8 string. Example:

```
valeur="VDEgQ2FwdCBDaGF1ZCAx"
    → "T1 Capt Chaud 1"
```

The design spec claimed values were double-HTML-escaped base64 (i.e. the
decoded base64 result would itself contain HTML entities like `&amp;`). This
was not observed on either tested box. Values decode cleanly in one step with
no HTML unescaping needed. This may have been true of an older firmware version
or a different endpoint variant; it is not true of `lecture_valeurs_donnees.php`
on firmware 3.0.13 or 3.0.18.

---

## Symbol families

The following families were identified in the dict file and confirmed against
real fixture data:

| Family | Example symbols | Typical decoded value | Notes |
|---|---|---|---|
| `tlbl_NN` | `tlbl_01`..`tlbl_29` | `"T1 Capt Chaud 1"` | Installer-assigned label for temperature probe N. Not a measurement. |
| `fllbl_N` | `fllbl_1`..`fllbl_6` | `"DEBIT 1"` | Installer-assigned label for flow meter N. Not a measurement. |
| `trilbl_NN` | `trilbl_01`..`trilbl_13` | `"C4 BAL Appoint"` | Installer-assigned label for valve/tri-state output N. Not a measurement. |
| `tr_N` | `tr_1`..`tr_16` | `"26.7 dC"` | Temperature in degrees Celsius. Note the literal suffix is `dC`, not `°C`. Sentinel: `"Dsc"` means disconnected probe. |
| `fl_N` | `fl_1`..`fl_6` | `"0.0 l mn"` | Flow rate in litres per minute. Note the literal suffix is `l mn`. Sentinel: `"Off"` means sensor disabled. |
| `rl_N` | `rl_0`, `rl_4` | `"On"`, `"Off"`, `"Marche"`, `"Arret"` | Relay state. Only `rl_0` and `rl_4` are active on the two captured boxes; the other six (`rl_1`..`rl_3`, `rl_5`..`rl_7`) are commented out in the dict for this firmware. |
| `tr_N` (high range) | `tr_14`..`tr_26` | `"20.5 dC"` | Same family as `tr_1`..`tr_13`, at a higher donnee ID range (1742..1754 vs 614..626). |
| `serial` | `serial` | (installation ID) | PII — the install ID string. Redact before committing any fixture. |
| `tr_N` (unknown) | `tr_*` variants | `"0pC"`, `"100pC"` | Possibly modulation duty cycle (percent). Semantics unconfirmed; not modelled in v0.1. |

Label strings (`tlbl_*`, `fllbl_*`, `trilbl_*`) carry the human-readable names
assigned by the installer, not measurements. They are used as friendly names
for the corresponding measurement codes.

Temperature values include a trailing `" dC"` suffix; strip it before parsing
to float. Flow values include a trailing `" l mn"` suffix similarly.

Some `tlbl_*` / `fllbl_*` / `trilbl_*` slots decode to an empty string: the
sensor slot is present in the firmware dict but not wired up on that
installation. This is normal and not a capture gap.

---

## Session expiry

The PHPSESSID cookie expires after some period of inactivity. When this
happens, the snapshot endpoint returns the login page HTML rather than XML
(i.e. the response contains `name="pass"`). The client should detect this,
re-authenticate, and retry the snapshot fetch once.

---

## `statut="echec"` responses

The snapshot endpoint returns `statut="echec"` for any server-side error. The
body contains a `<message>` element with a French-language explanation. Common
causes observed during development:

- Missing `id` field: "L'identifiant de l'installation est absent de la requete"
- `periode` base64-encoded instead of plain integer: "Le format de la periode
  de l'envoi rapide est incorrect"
- Invalid or expired `id`: similar format mismatch message

---

## Fixture regeneration

See `tests/fixtures/README.md` for the full curl recipe and anonymisation
checklist.

Important: the XML snapshot contains base64-encoded values. A plain-text grep
for PII will miss anything encoded (install ID, MAC address, IP octets, owner
name). Every `<valeur>` attribute must be individually decoded and inspected
before committing a fixture. The donnee codes that carry PII on both captured
boxes are: `donnee="1"` (vendor hostname), `donnee="3"` (install ID),
`donnee="4"` (owner label), `donnee="499"` (MAC address), `donnee="508"` to
`"515"` (gateway/DNS IP octets).

---

## Credits and licensing of the protocol facts

This integration is licensed Apache-2.0 (see `LICENSE`). The protocol
**facts** (endpoint URLs, form-field names, request body shape, dict-file
format, value encoding) recorded above are not original to this project,
but neither are they copyrightable expression — they are dictated by the
box. They originate from two sources:

- [jean1492/SolisArt-HomeAssistant](https://github.com/jean1492/SolisArt-HomeAssistant)
  (GPL-3.0) — the original read-side reverse engineering of the SolisArt HTTP
  protocol, in particular the login flow and snapshot endpoint structure.
- An unpublished personal script by Phil Elson (2022) — additional details,
  specifically the `commun-donnees.<hash>.js` discovery path (reading the hash
  from the installation page script tags) and the install-ID extraction method
  from landing-page hrefs.

No source code from jean1492's project is carried over to this repository.
The implementation here is from-scratch, written against captured XML and
JS fixtures from two physical boxes (firmware 3.0.13 and 3.0.18) using an
async aiohttp client, typed dataclasses, and Home Assistant's config-flow
+ coordinator pattern — none of which are present in jean1492's code.
