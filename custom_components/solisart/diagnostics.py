from __future__ import annotations

import re

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_INSTALL_ID,
    CONF_PASSWORD_CLOUD,
    CONF_PASSWORD_LOCAL,
    CONF_USERNAME_CLOUD,
    CONF_USERNAME_LOCAL,
    DOMAIN,
)

TO_REDACT = {
    CONF_PASSWORD_LOCAL,
    CONF_PASSWORD_CLOUD,
    CONF_USERNAME_LOCAL,
    CONF_USERNAME_CLOUD,
    CONF_INSTALL_ID,
}

# Allow-list of donnee-symbol prefixes considered safe to share in a public
# diagnostics dump. Anything outside this set is dropped from snap.raw before
# the dump is written. Specifically excluded by being absent:
#   - "serial" / "num_serie" — installation ID
#   - "srv_*" — vendor cloud config (server name, port, request URLs)
#   - "config_mac" + IP octet symbols (508–515 on observed firmwares)
#   - "label_install" / "nom_*" / "adresse_*" / "ville_*" / "cp_*" /
#     "gps_*" / "email_*" / "tel_*" — owner identity/contact details
SAFE_DIAG_CODE_RE = re.compile(
    r"^(?:"
    r"t_\d+|"          # temperatures
    r"tlbl_\d+|"       # temperature-probe labels
    r"fl_\d+|"         # flows
    r"fllbl_\d+|"      # flow-probe labels
    r"trilbl_\d+|"     # tri-valve labels
    r"rl_\d+|"         # relay states
    r"tr_\d+"          # modulation-percent codes (deferred to v0.2)
    r")$"
)


def _redact_raw(raw: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in raw.items() if SAFE_DIAG_CODE_RE.match(k)}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    bucket = hass.data[DOMAIN].get(entry.entry_id, {})
    coordinator = bucket.get("coordinator")
    snap = coordinator.data if coordinator is not None else None
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "snapshot": {
            "serial": "REDACTED" if snap and snap.serial else None,
            "raw": _redact_raw(snap.raw) if snap else {},
            "sensors": (
                {k: r.value for k, r in snap.sensors.items()} if snap else {}
            ),
            "binary": dict(snap.binary) if snap else {},
        },
        "last_update_success": (
            coordinator.last_update_success if coordinator is not None else None
        ),
        "last_exception": (
            str(coordinator.last_exception)
            if coordinator is not None and coordinator.last_exception is not None
            else None
        ),
    }
