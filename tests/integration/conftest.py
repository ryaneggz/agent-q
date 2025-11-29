import pytest
from httpx import AsyncClient, ASGITransport

from shinzo.main import app


@pytest.fixture
async def api_client():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

