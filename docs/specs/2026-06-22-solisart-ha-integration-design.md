# SolisArt Home Assistant Integration — Design

**Date:** 2026-06-22
**Status:** Approved by user, ready for planning
**Repo (target):** github.com/pelson/SolisArt-HA-integration (not yet created)
**Local path:** /media/important/github/pelson/IOT/SolisArt-HA-integration

## Background

SolisArt sells solar thermal heating controllers based on Raspberry Pi
hardware. The device runs Apache 2.2 on Debian 7, exposing a PHP admin
interface at `http://<box>/` with a French web UI. The same protocol is
offered by the cloud at `https://my.solisart.fr`.

An existing community project by jean1492 demonstrates that data can be
scraped from the cloud endpoint via two HTTP calls:

- `POST /` (login form fields `id`, `pass`, `ihm=admin`, `connexion`)
  sets a PHPSESSID cookie
- `POST /admin/divers/ajax/lecture_valeurs_donnees.php` returns the full
  sensor snapshot as XML, where each datum is base64-encoded
- `GET /admin/divers/js/solisart/commun-donnees.<hash>.js` provides
  the human-readable name dictionary

We have verified the same protocol works locally against a real box.
Credit:

- Read-side protocol understanding derives from
  [jean1492/SolisArt-HomeAssistant](https://github.com/jean1492/SolisArt-HomeAssistant)
  (GPL-3.0). Our integration will be GPL-3.0 and prominently credit
  that project.
- Additional protocol details (including the
  `lecture_descriptions_donnees.php` endpoint as an alternative to the
  hashed `commun-donnees.<hash>.js` dictionary, and the double-HTML-
  escaped base64 payload encoding) come from prior reverse-engineering
  by pelson (2022, unpublished personal script).

## Goals

1. A proper Home Assistant custom integration (config flow, coordinator,
   typed entities), not a shell-script package.
2. Direct 1:1 mirror of what the SolisArt box exposes — no Home
   Assistant-side abstractions (no synthesised "season" or "holiday"
   logic; those belong in user automations).
3. Read and write: sensors plus climate entities per zone, with safe
   setpoint round-trip tests.
4. Configurable endpoint mode: local-only, cloud-only, or local with
   cloud fallback.
5. Polite to the box's network stack — manual refresh by default given
   known fragile Raspberry Pi B hardware in some installations.
6. HACS-installable as a custom repository.
7. French-language UI strings as primary, English as fallback.

## Non-goals

- Multi-installation support per HA instance. Each HA has at most one
  SolisArt; the design assumes a single config entry.
- Automatic season / holiday / weather adaptation logic. The user will
  build those in HA automations on top of the integration.
- Public HACS listing (default-store PR) or
  [home-assistant/brands](https://github.com/home-assistant/brands)
  submission for v0.x. Custom-repo install only.
- Discovery (mDNS / SSDP). The box doesn't advertise; manual host entry
  is fine.

## Repository layout

```
SolisArt-HA-integration/
├── custom_components/solisart/
│   ├── __init__.py            # async_setup_entry, coordinator wiring
│   ├── manifest.json
│   ├── config_flow.py         # UI setup (French-first)
│   ├── coordinator.py         # DataUpdateCoordinator
│   ├── api/                   # reusable client subpackage
│   │   ├── __init__.py
│   │   ├── client.py          # SolisartClient (login, fetch, writes)
│   │   ├── endpoint.py        # local / cloud / fallback resolver
│   │   ├── parser.py          # XML + commun-donnees.js → typed objs
│   │   └── model.py           # Snapshot, SensorReading, ZoneState…
│   ├── sensor.py
│   ├── binary_sensor.py
│   ├── climate.py             # one entity per active zone
│   ├── button.py              # button.solisart_rafraichir
│   ├── services.yaml          # only for actions without a 1:1 entity
│   ├── strings.json           # canonical French strings
│   ├── translations/
│   │   ├── fr.json
│   │   └── en.json
│   └── const.py
├── tests/
│   ├── fixtures/              # captured XML / JS dict (optional)
│   └── test_smoke_live.py     # opt-in via env vars, hits real box
├── docs/
│   ├── README.md
│   ├── REVERSE_ENGINEERING.md # writes endpoint findings + credits
│   └── specs/                 # design docs
├── hacs.json
├── pyproject.toml             # for the api/ subpackage + ruff
├── LICENSE                    # GPL-3.0
└── README.md                  # top-level, installation instructions
```

The `api/` subpackage stays inside `custom_components/solisart/` for
now. If a second consumer ever appears (e.g. a CLI), we promote it to a
standalone pip package then, not before.

## Runtime architecture

```
HA core
  └── async_setup_entry()
        └── SolisartCoordinator (DataUpdateCoordinator)
              ├── poll mode: manual | slow timer | fast timer
              ├── holds Snapshot dataclass
              └── SolisartClient
                    ├── aiohttp.ClientSession (persistent cookies)
                    ├── EndpointStrategy (local / cloud / fallback)
                    └── parser: XML + JS dict → Snapshot

Entities (read coordinator.data)
  ├── SensorEntity (temps, flows, valve enums)
  ├── BinarySensorEntity (rl* relay codes)
  ├── ClimateEntity (one per zone)
  └── ButtonEntity (rafraîchir)
```

Key behaviour:

- **One refresh = one HTTP POST** to
  `lecture_valeurs_donnees.php`. The full Snapshot is produced per
  cycle; all entities derive from it. No per-entity HTTP.
- **Dict caching**: `commun-donnees.<hash>.js` is fetched on first
  login and cached in memory until the landing page reports a new
  hashed filename, at which point we refetch and update the parser.
- **Session reuse**: a single `aiohttp.ClientSession` per client
  instance. Re-login on 401 or when a response is the login page (PHP
  session timeout).
- **Writes** go through the same client / session / fallback chain.
  Writes are not automatically retried on failure: heating system,
  fail loudly. After a successful write, the coordinator schedules
  one refresh to surface the new state.

### Polling strategy

The default `update mode` is `manual`. Three options:

- `manual` (default): no automatic polling. User triggers refresh via
  `button.solisart_rafraichir` or HA's built-in
  `homeassistant.update_entity` service.
- `slow timer`: configurable interval, default 30 min, range 5–360 min.
- `fast timer`: configurable interval, range 1–60 min, for healthy
  hardware.

Rationale: SolisArt installations on Raspberry Pi B hardware have shown
network card instability under continuous polling. Manual-by-default
protects fragile boxes; users opt in to timer polling once they trust
their hardware.

After a successful write, the coordinator schedules a one-shot refresh
~15 s later regardless of mode, so the UI reflects the box's accepted
state.

## Config flow

UI flow at Settings → Devices & services → Add → SolisArt. All strings
French-first; English available via the standard HA language picker.

### Step 1: Endpoint (Mode de connexion)

- `Mode`: `local` / `cloud` / `local avec bascule cloud`
- `Adresse de la box` (host or IP): required if mode includes local
- `URL cloud`: pre-filled `https://my.solisart.fr`, editable

### Step 2: Identifiants

The credentials block adapts to the chosen mode. Local and cloud
credentials may differ.

- `mode = local`:
  - `Identifiant local`, `Mot de passe local`
- `mode = cloud`:
  - `Identifiant my.solisart.fr`, `Mot de passe my.solisart.fr`,
    `Identifiant d'installation`
- `mode = local avec bascule cloud`:
  - Both blocks shown. Cloud block may be left blank to disable
    fallback while still showing the option.

For local mode, the installation ID is auto-detected from the landing
page redirect (`/admin/?page=installation&id=<ID>`). For cloud mode it
must be supplied.

The flow tests login against each configured endpoint before saving the
entry. Errors: `invalid_auth`, `cannot_connect`,
`cannot_resolve_install_id`.

### Step 3: Comportement de mise à jour

- `Mode de rafraîchissement`: `manuel` / `minuterie lente` / `minuterie rapide`
- `Intervalle (minutes)`: shown only for timer modes
- `Exposer toutes les données disponibles (capteurs diagnostic)`:
  default off
- `Activer les commandes` (writes enabled): default off in v0.1, default
  on in v0.2 once writes are reverse-engineered and smoke-tested

### Options flow

Same Step 3 fields editable without removing the entry.

### Reauth

Triggered when a poll returns the login page. Shows whichever
credentials block(s) correspond to the failing endpoint.

### Diagnostics download

Captures: anonymised snapshot, dict version, endpoint mode, last error.
Both passwords are redacted.

## Entity model

Principle: **every entity corresponds 1:1 to a real datum or action on
the SolisArt box**. No invented composites.

### Sensors

| Entity (auto-named from box) | SolisArt source | Unit |
|---|---|---|
| `sensor.solisart_<tlbl_NN_label>` | `tlbl_01..16` temperature probes | °C |
| `sensor.solisart_<fllbl_N_label>` | `fllbl_1..6` flow probes | L/min |
| `sensor.solisart_<trilbl_NN_label>` | `trilbl_01..13` valve / relay states | enum from box |

Entity slugs derive from the box's own French labels (e.g.
`sensor.solisart_t1_capt_chaud_1`). No renaming, no English promotion.

### Binary sensors

Only for codes that are genuinely boolean (the `rl*` relay codes
discovered in the dict). No synthesised composites.

### Climate entities

One per active zone, discovered from `tlbl_11..14` and `trilbl_05..07`
labels. HVAC modes, preset modes, and target-temperature behaviour are
populated from **what the SolisArt actually exposes**, to be determined
during reverse engineering. If the box only supports marche/arrêt, the
entity will only support `heat` / `off`. We will not invent presets.

In v0.1, climate entities are read-only (target temperature shown, not
settable) unless the user enables `Activer les commandes` in the
options flow. In v0.2, writes become enabled by default once the
write endpoints are reverse-engineered and the round-trip smoke test
is green.

### Button

`button.solisart_rafraichir`: triggers an on-demand coordinator refresh.
Pressable from UI; usable in automations
(`service: button.press` from any trigger).

### Services

Only for box actions that have no natural HA entity counterpart, and
only after confirming the box supports them. Service domain: `solisart`.

### Advanced opt-in

When enabled in the options flow, every dict-named code is exposed as a
diagnostic sensor (`entity_category=diagnostic`, disabled by default in
the UI). Useful for discovering codes we missed.

### Device registry

Single device per config entry, identified by serial. All entities
attached to it. Hardware fields (model, firmware) populated from the
box's landing-page metadata where available.

## Refresh granularity

Confirmed single API call per refresh: one POST to
`/admin/divers/ajax/lecture_valeurs_donnees.php` returns the full
snapshot (~hundreds of fields). No per-zone or per-sensor endpoint
exists in the protocol.

Writes use distinct POST endpoints (to be reverse-engineered) and are
independent of the refresh call.

## Tests

Minimal smoke tests only, opt-in via environment variables, no mocked
HTTP, no CI workflow. Two tests:

```
tests/test_smoke_live.py

  test_login_and_fetch_snapshot
    - logs in, fetches snapshot, asserts serial + ≥1 temperature reading

  test_setpoint_round_trip
    - reads zone 0 target temperature (original)
    - writes original + 0.5 °C
    - waits, re-reads, asserts new value
    - restores original in finally{} regardless of test outcome
```

Both tests are gated on `SOLISART_TEST_HOST`, `SOLISART_TEST_USER`,
`SOLISART_TEST_PASS` env vars and skipped if absent. Run before each
release on the real installation:

```bash
SOLISART_TEST_HOST=<box-ip> \
  SOLISART_TEST_USER=<user> SOLISART_TEST_PASS=<password> \
  pytest tests/
```

Trade-off explicitly accepted: write paths are reverse-engineered and
shipped without a regression net. Mitigation: writes are gated behind
an "Activer les commandes" config option (off by default for v0.1),
and the user is asked to run the smoke tests before each release.

## Distribution

HACS-compatible custom repository. Files at repo root:

```
hacs.json
  {
    "name": "SolisArt",
    "render_readme": true,
    "country": ["FR"],
    "homeassistant": "2024.1.0"
  }

custom_components/solisart/manifest.json
  {
    "domain": "solisart",
    "name": "SolisArt",
    "version": "0.1.0",
    "codeowners": ["@pelson"],
    "config_flow": true,
    "documentation": "https://github.com/pelson/SolisArt-HA-integration",
    "issue_tracker": "https://github.com/pelson/SolisArt-HA-integration/issues",
    "iot_class": "local_polling",
    "requirements": []
  }
```

Install path for users:

1. HACS → ⋮ → Custom repositories → add
   `github.com/pelson/SolisArt-HA-integration` as Integration.
2. Install from HACS → restart HA → Settings → Devices → Add →
   SolisArt.

Releases tagged on GitHub (`v0.1.0`, …); HACS picks them up. A release
script reconciles `manifest.json` `version` with the tag.

No HACS default-store PR, no brands submission, until/unless we want
broader visibility later.

## Out of scope for v0.x

- Discovery (mDNS / SSDP)
- Energy dashboard integration
- Long-term statistics beyond what `state_class=measurement` gives for
  free
- Local push (the box has no notification mechanism we know of)
- Migrating from jean1492's YAML package automatically
- Multi-zone climate scheduling logic on the HA side

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Fragile Pi B network card under polling | Manual refresh by default; configurable timer with a generous lower bound |
| Write endpoints reverse-engineered without a test net before discovery | Round-trip restoration test; writes gated by config option in v0.1 |
| PHP session expiry mid-poll | Detect login page, re-login transparently, retry once |
| `commun-donnees.js` hash changes after firmware update | Re-fetch on landing-page hash mismatch; tolerate missing codes in parser |
| Cloud endpoint protocol drifts from local | Endpoint strategy isolates the two; tests can be run against either |
| HA core breaking changes (e.g. async API deprecations) | Pin minimum HA in `manifest.json`; bump on each release |

## Acceptance for v0.1

- Install via HACS custom repo, configure via UI in French
- Local-only mode: read full snapshot, see curated entities, refresh
  via button
- Climate entity exists per zone; reading current + target works
- Smoke tests pass against a real installation
- README documents install, configuration, and the
  `Activer les commandes` toggle

Writes (`set_temperature` on the climate entity) ship as a documented
v0.2 milestone once the reverse-engineering work in
`REVERSE_ENGINEERING.md` is done and the round-trip smoke test is
green.
