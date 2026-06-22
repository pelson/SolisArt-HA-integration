from __future__ import annotations

import base64
import logging
import re

import aiohttp

from .dict_parser import parse_donnee_dict
from .endpoint import EndpointStrategy
from .model import Snapshot
from .snapshot import build_snapshot
from .xml_parser import parse_snapshot_xml

_LOGGER = logging.getLogger(__name__)
_DICT_RE = re.compile(r"commun-donnees\.[a-zA-Z0-9_]+\.js")
# Install ID appears in landing-page hrefs as `?page=installation&id=<ID>`
# or similar. IDs are alphanumeric (e.g. "SC1Z00000000"), not purely
# numeric — do NOT restrict to \d.
_INSTALL_ID_RE = re.compile(r"[?&]id=([A-Za-z0-9_-]+)")


class SolisartAuthError(Exception):
    pass


class SolisartConnectionError(Exception):
    pass


class SolisartClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        endpoint: EndpointStrategy,
        username: str,
        password: str,
        install_id: str | None = None,
    ):
        self._session = session
        self._endpoint = endpoint
        self._username = username
        self._password = password
        self._install_id = install_id
        self._base: str | None = None
        self._id_to_symbol: dict[int, str] = {}
        self._dict_filename: str | None = None

    @property
    def install_id(self) -> str | None:
        return self._install_id

    async def _try_login_on(self, base: str) -> str | None:
        """Returns landing-page HTML on success, None on auth failure."""
        data = {
            "id": self._username,
            "pass": self._password,
            "ihm": "admin",
            "connexion": "1",
        }
        try:
            async with self._session.post(
                f"{base}/", data=data, allow_redirects=True
            ) as resp:
                if resp.status >= 500:
                    raise SolisartConnectionError(f"{base} returned {resp.status}")
                text = await resp.text()
        except aiohttp.ClientError as exc:
            raise SolisartConnectionError(str(exc)) from exc
        if 'name="pass"' in text and 'name="id"' in text:
            return None  # login form re-rendered → auth failure
        return text

    async def login(self) -> None:
        last_err: Exception | None = None
        for base in self._endpoint.candidates():
            try:
                landing = await self._try_login_on(base)
            except SolisartConnectionError as exc:
                last_err = exc
                continue
            if landing is None:
                last_err = SolisartAuthError(f"auth failed on {base}")
                continue
            self._base = base
            if self._install_id is None:
                m = _INSTALL_ID_RE.search(landing)
                if m:
                    self._install_id = m.group(1)
            await self._refresh_dict_if_needed(landing)
            return
        raise last_err or SolisartConnectionError("no endpoints configured")

    async def _refresh_dict_if_needed(self, landing_html: str) -> None:
        m = _DICT_RE.search(landing_html)
        if not m:
            return
        filename = m.group(0)
        if filename == self._dict_filename and self._id_to_symbol:
            return
        url = f"{self._base}/admin/divers/js/solisart/{filename}"
        try:
            async with self._session.get(url) as resp:
                resp.raise_for_status()
                js_text = await resp.text()
        except aiohttp.ClientError as exc:
            raise SolisartConnectionError(f"dict fetch failed: {exc}") from exc
        self._id_to_symbol = parse_donnee_dict(js_text)
        self._dict_filename = filename

    def _snapshot_body(self) -> dict[str, str]:
        if self._install_id is None:
            raise SolisartConnectionError("install_id unknown; cannot fetch snapshot")
        return {
            "id": base64.b64encode(self._install_id.encode()).decode(),
            "heure": "0",
            "periode": "5",
        }

    async def fetch_snapshot(self) -> Snapshot:
        if self._base is None:
            await self.login()
        assert self._base is not None
        url = f"{self._base}/admin/divers/ajax/lecture_valeurs_donnees.php"
        body = self._snapshot_body()
        try:
            async with self._session.post(url, data=body) as resp:
                text = await resp.text()
        except aiohttp.ClientError as exc:
            raise SolisartConnectionError(str(exc)) from exc

        # PHP session expired → login page re-renders. Re-auth once, retry.
        if 'name="pass"' in text and 'name="id"' in text:
            _LOGGER.info("solisart session expired, re-logging in")
            self._base = None
            await self.login()
            assert self._base is not None
            url = f"{self._base}/admin/divers/ajax/lecture_valeurs_donnees.php"
            body = self._snapshot_body()
            async with self._session.post(url, data=body) as resp:
                text = await resp.text()

        if not text.lstrip().startswith("<"):
            raise SolisartConnectionError("unexpected non-XML response")
        response = parse_snapshot_xml(text)
        if response.statut != "succes":
            raise SolisartConnectionError(
                f"box returned statut={response.statut!r}"
            )
        return build_snapshot(response, self._id_to_symbol)

    async def close(self) -> None:
        # Session is owned by the caller; nothing to close here.
        pass
