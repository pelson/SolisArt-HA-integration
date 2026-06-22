import re

# Only matches lines NOT preceded by `//`. Captures symbol and integer id.
# `const donnee_<symbol> = <int>;` — leading whitespace allowed; the value
# must be an unquoted integer (string-valued constants like
# `const version_application = "3.0.13";` are deliberately ignored).
_DECL_RE = re.compile(
    r"^\s*const\s+donnee_([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\d+)\s*;",
    re.MULTILINE,
)


def parse_donnee_dict(js_text: str) -> dict[int, str]:
    """Extract numeric-id → symbolic-name mappings from commun-donnees.js.

    The dict file is generated source: one `const donnee_<symbol> = <id>;`
    per line. Lines starting with `//` (after optional whitespace) are
    commented-out constants flagging codes the firmware does not support
    and are skipped.
    """
    out: dict[int, str] = {}
    for line in js_text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        m = _DECL_RE.match(line)
        if m:
            out[int(m.group(2))] = m.group(1)
    return out
