# SolisArt Home Assistant Integration

HACS-installable custom integration for SolisArt solar thermal controllers.

## Status

v0.1.1 — read-only. Writes and setpoint control are deferred to v0.2.

License: Apache-2.0. The protocol facts implemented here (endpoint URLs,
form-field names, request shape) originate from the reverse-engineering
work of [jean1492/SolisArt-HomeAssistant](https://github.com/jean1492/SolisArt-HomeAssistant)
(GPL-3.0) and pelson's 2022 unpublished notes. No source code from
either project is carried over — this is a from-scratch implementation
against captured fixtures from real boxes (firmware 3.0.13 and 3.0.18).

## What you get

Each integration entry exposes the following entities, derived from a single
snapshot POST to the box:

- One `sensor` per temperature probe (`t_N`, N = 1..16): value in °C,
  friendly name taken from the installer-assigned French label (`tlbl_NN`).
- One `sensor` per flow meter (`fl_N`, N = 1..6): value in L/min.
- One `binary_sensor` per active relay (`rl_N`): on/off state.
- One read-only `climate` entity per heating zone (zones 11..14 in the box's
  numbering): current temperature only; setpoints and mode writes are out of
  scope for v0.1.
- One `button` entity ("Rafraichir / Refresh"): triggers an immediate snapshot
  fetch outside of the configured refresh schedule.

## Installation

### HACS (recommended)

1. Open Home Assistant. Go to **Settings** → **HACS** → menu (three dots,
   top right) → **Custom repositories**.
2. Add `https://github.com/pelson/SolisArt-HA-integration` as type
   **Integration**.
3. Search for "SolisArt" in HACS and install.
4. Restart Home Assistant.
5. Go to **Settings** → **Devices & Services** → **Add Integration** and
   search for "SolisArt".

### Development / symlink shortcut

For local development without HACS:

```bash
ln -s "$(pwd)/custom_components/solisart" \
      ~/.homeassistant/custom_components/solisart
```

Restart HA after the symlink is in place.

## Configuration

The config flow walks through three screens. Each screen only shows the
fields that apply to your chosen mode.

### Step 1: Connection mode

Pick one of:

- **Local** — direct LAN access to the box. You will be asked for the box
  address and local credentials on the next screen.
- **Cloud** — go through `my.solisart.fr`. You will be asked for cloud
  credentials and your installation ID.
- **Local with cloud fallback** — try local first, fall back to cloud if the
  box is unreachable. You will be asked for both sets of credentials.

### Step 2: Local box (local / fallback modes)

- **Box address** — full URL including scheme, e.g. `http://192.0.2.10`. The
  `http://` prefix is required; a bare IP will currently fail. (Tracked for
  v0.2.)
- **Local username / password** — default `util` / `util`; change these in
  the box's admin interface before exposing it to a network you do not fully
  control.

### Step 3: my.solisart.fr cloud (cloud / fallback modes)

- **Cloud URL** — defaults to `https://my.solisart.fr`.
- **Cloud username / password** — the credentials you use on the website.
- **Installation ID** — visible in the URL bar once you log in to the cloud
  UI.

### Step 4: Refresh behaviour

- **Refresh mode** — `Manuel` (no polling) or `Minuterie` (interval polling).
- **Interval (minutes)** — shown only when `Minuterie` is selected; 1–360,
  default 30.

## Refresh modes

| Mode | Label | Description |
|---|---|---|
| `manual` | Manuel | No automatic polling. Use the Refresh button to fetch on demand. Default. |
| `timer` | Minuterie | Poll on a fixed interval, 1–360 minutes (default: 30). |

The default is `Manuel` (button-driven). This is deliberate: the integration
was developed on a Raspberry Pi B, which saturates its CPU on repeated async
HTTP polls. If your hardware is more capable, `Minuterie` at 30-minute
intervals is a reasonable starting point.

## Known limitations

- **No device discovery.** The box address must be entered manually; mDNS/DHCP
  discovery is not implemented in v0.1.
- **No writes or setpoints.** Climate entities are read-only. Scheduling
  changes, zone setpoints, and relay commands are deferred to v0.2.
- **`tr_*` codes partially modelled.** Values with the pattern `"0pC"` or
  `"100pC"` (possibly modulation duty cycles) appear in the box snapshot but
  are not exposed as entities in v0.1.
- **No brand icon.** A pull request to `home-assistant/brands` has not been
  submitted yet; the integration shows a generic icon in the HA UI.
- **`http://` prefix required.** The config flow does not prepend the scheme
  automatically. Entering a bare IP will result in a connection error.

## Development

```bash
uv venv
uv pip install -e ".[dev]"
uv run pytest tests/ -q
```

The test suite runs against anonymised fixtures from a real box (firmware
3.0.18) and does not require network access. To run the live smoke test
against a real box, populate `secrets.env` (gitignored) with:

```bash
export SOLISART_TEST_HOST=<box-ip>     # bare host or IP, no http:// prefix
export SOLISART_TEST_USER=<username>
export SOLISART_TEST_PASS=<password>
export SOLISART_TEST_INSTALL_ID=<install-id>
```

then:

```bash
set -a; source secrets.env; set +a
uv run pytest tests/test_smoke_live.py -v
```

## Credits and license

Apache-2.0. See `LICENSE`.

Protocol understanding (URLs, form fields, request body shape, dict-file
format, value-encoding rules) was learned from two sources, but no source
code from either is included in this repository:

- [jean1492/SolisArt-HomeAssistant](https://github.com/jean1492/SolisArt-HomeAssistant)
  (GPL-3.0) — the original read-side reverse engineering of the SolisArt HTTP
  protocol. Their codebase is a 89-line synchronous `urllib` script plus
  YAML template packages; this integration is an async, typed,
  config-flow-driven Home Assistant custom component re-implemented from
  scratch against captured XML/JS fixtures from two physical boxes.
- An unpublished personal script by Phil Elson (2022) — additional protocol
  details, in particular the `commun-donnees.<hash>.js` dict-file discovery
  path and the install-ID extraction method.
