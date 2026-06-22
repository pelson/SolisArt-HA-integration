from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.client import SolisartAuthError, SolisartClient, SolisartConnectionError
from .api.model import Snapshot
from .const import (
    POST_WRITE_REFRESH_DELAY,
    UPDATE_MODE_FAST,
    UPDATE_MODE_MANUAL,
    UPDATE_MODE_SLOW,
)

_LOGGER = logging.getLogger(__name__)


def _interval_for(mode: str, minutes: int) -> timedelta | None:
    if mode == UPDATE_MODE_MANUAL:
        return None
    if mode in (UPDATE_MODE_SLOW, UPDATE_MODE_FAST):
        return timedelta(minutes=minutes)
    raise ValueError(f"unknown update mode: {mode}")


class SolisartCoordinator(DataUpdateCoordinator[Snapshot]):
    def __init__(
        self,
        hass: HomeAssistant,
        client: SolisartClient,
        update_mode: str,
        interval_min: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="solisart",
            update_interval=_interval_for(update_mode, interval_min),
        )
        self._client = client

    async def _async_update_data(self) -> Snapshot:
        try:
            return await self._client.fetch_snapshot()
        except SolisartAuthError as exc:
            raise UpdateFailed(f"auth failure: {exc}") from exc
        except SolisartConnectionError as exc:
            raise UpdateFailed(f"connection failure: {exc}") from exc

    async def async_schedule_post_write_refresh(self) -> None:
        async def _later() -> None:
            await asyncio.sleep(POST_WRITE_REFRESH_DELAY.total_seconds())
            await self.async_request_refresh()
        self.hass.async_create_task(_later())
