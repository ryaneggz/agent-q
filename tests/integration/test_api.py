import pytest
from httpx import AsyncClient
from app.main import app
from app.models import Priority


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test the root endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Agent Queue System"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_submit_message():
    """Test submitting a message"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/messages",
            json={
                "message": "Test message",
                "priority": "normal"
            }
        )

    assert response.status_code == 202
    data = response.json()
    assert "message_id" in data
    assert data["state"] == "queued"
    assert "queue_position" in data


@pytest.mark.asyncio
async def test_submit_message_with_high_priority():
    """Test submitting a high priority message"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/messages",
            json={
                "message": "Urgent message",
                "priority": "high"
            }
        )

    assert response.status_code == 202
    data = response.json()
    assert "message_id" in data


@pytest.mark.asyncio
async def test_get_message_status():
    """Test getting message status"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Submit a message
        submit_response = await client.post(
            "/messages",
            json={"message": "Test message"}
        )
        message_id = submit_response.json()["message_id"]

        # Get status
        status_response = await client.get(f"/messages/{message_id}/status")

    assert status_response.status_code == 200
    data = status_response.json()
    assert data["message_id"] == message_id
    assert data["state"] in ["queued", "processing", "completed"]
    assert data["user_message"] == "Test message"


@pytest.mark.asyncio
async def test_get_nonexistent_message_status():
    """Test getting status of non-existent message"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/messages/nonexistent-id/status")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_queued_message():
    """Test cancelling a queued message"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Submit a message
        submit_response = await client.post(
            "/messages",
            json={"message": "Test message"}
        )
        message_id = submit_response.json()["message_id"]

        # Cancel immediately (before it processes)
        cancel_response = await client.delete(f"/messages/{message_id}")

    # May succeed or fail depending on timing
    assert cancel_response.status_code in [200, 409]


@pytest.mark.asyncio
async def test_get_queue_summary():
    """Test getting queue summary"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/queue")

    assert response.status_code == 200
    data = response.json()
    assert "total_queued" in data
    assert "total_processing" in data
    assert "total_completed" in data
    assert "queued_messages" in data


@pytest.mark.asyncio
async def test_message_validation():
    """Test message validation"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Empty message should fail
        response = await client.post(
            "/messages",
            json={"message": ""}
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_priority_validation():
    """Test priority validation"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Invalid priority should fail
        response = await client.post(
            "/messages",
            json={
                "message": "Test",
                "priority": "invalid"
            }
        )

    assert response.status_code == 422
