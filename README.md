# SolisArt Home Assistant Integration

HACS-installable custom integration for SolisArt solar thermal controllers.

## Status

v0.1 — read-only. Writes and setpoint control are deferred to v0.2.

License: GPL-3.0. Read-side protocol understanding derived from
[jean1492/SolisArt-HomeAssistant](https://github.com/jean1492/SolisArt-HomeAssistant)
and pelson's 2022 unpublished reverse-engineering notes.

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

The config flow walks through three screens:

### Step 1: Connection mode

- **Mode** — choose `local` (direct LAN), `cloud`, or `local-with-cloud-fallback`.
- **Box address** (local/fallback modes) — enter the full URL including the
  scheme, e.g. `http://192.0.2.10`. The `http://` prefix is required; entering
  a bare IP address will fail. This is a known v0.1 rough edge tracked for
  improvement in v0.2.
- **Cloud URL** (cloud/fallback modes) — defaults to `https://my.solisart.fr`.

### Step 2: Credentials

Enter the username and password for the box. The box ships with a default
account (`util`/`util`); change these in the box's admin interface before
exposing it on a network you do not fully control.

### Step 3: Refresh behaviour

- **Refresh mode** — see "Refresh modes" below.
- **Interval** — shown when a timer mode is selected.

## Refresh modes

The integration offers three refresh strategies:

| Mode | Label | Description |
|---|---|---|
| `manual` | Manuel | No automatic polling. Use the Refresh button to fetch on demand. Default. |
| `slow` | Minuterie lente | Poll on a fixed interval between 5 and 360 minutes (default: 30). |
| `fast` | Minuterie rapide | Poll on a fixed interval between 1 and 60 minutes. |

The default is `manuel` (button-driven). This is deliberate: the integration
was developed on a Raspberry Pi B, which saturates its CPU on repeated async
HTTP polls. If your hardware is more capable, `minuterie lente` at 30-minute
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
export SOLISART_TEST_HOST=http://<box-ip>
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

GPL-3.0. See `LICENSE`.

Protocol understanding is derived from two sources:

- [jean1492/SolisArt-HomeAssistant](https://github.com/jean1492/SolisArt-HomeAssistant)
  (GPL-3.0) — the original read-side reverse engineering of the SolisArt HTTP
  protocol.
- An unpublished personal script by Phil Elson (2022) — additional protocol
  details, in particular the `commun-donnees.<hash>.js` dict-file discovery
  path and the install-ID extraction method.
