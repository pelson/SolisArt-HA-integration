import os

import pytest

from custom_components.solisart.api.client import SolisartClient, make_session
from custom_components.solisart.api.endpoint import EndpointStrategy

HOST = os.environ.get("SOLISART_TEST_HOST")
USER = os.environ.get("SOLISART_TEST_USER")
PASS = os.environ.get("SOLISART_TEST_PASS")

pytestmark = pytest.mark.skipif(
    not (HOST and USER and PASS),
    reason="set SOLISART_TEST_HOST/USER/PASS in secrets.env to run",
)


@pytest.mark.asyncio
async def test_login_and_fetch_snapshot():
    async with make_session() as session:
        client = SolisartClient(
            session=session,
            endpoint=EndpointStrategy("local", f"http://{HOST}", None),
            username=USER,
            password=PASS,
        )
        await client.login()
        snap = await client.fetch_snapshot()
        assert len(snap.sensors) >= 1
        assert any(r.unit == "°C" for r in snap.sensors.values())
