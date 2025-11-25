import pytest
from app.models import Priority


@pytest.mark.asyncio
async def test_root_endpoint(api_client):
    """Test the root endpoint"""
    response = await api_client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Agent Queue System"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health_check(api_client):
    """Test health check endpoint"""
    response = await api_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_submit_message(api_client):
    """Test submitting a message"""
    response = await api_client.post(
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
async def test_submit_message_with_high_priority(api_client):
    """Test submitting a high priority message"""
    response = await api_client.post(
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
async def test_get_message_status(api_client):
    """Test getting message status"""
    # Submit a message
    submit_response = await api_client.post(
        "/messages",
        json={"message": "Test message"}
    )
    message_id = submit_response.json()["message_id"]

    # Get status
    status_response = await api_client.get(f"/messages/{message_id}/status")

    assert status_response.status_code == 200
    data = status_response.json()
    assert data["message_id"] == message_id
    assert data["state"] in ["queued", "processing", "completed"]
    assert data["user_message"] == "Test message"


@pytest.mark.asyncio
async def test_get_nonexistent_message_status(api_client):
    """Test getting status of non-existent message"""
    response = await api_client.get("/messages/nonexistent-id/status")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_queued_message(api_client):
    """Test cancelling a queued message"""
    # Submit a message
    submit_response = await api_client.post(
        "/messages",
        json={"message": "Test message"}
    )
    message_id = submit_response.json()["message_id"]

    # Cancel immediately (before it processes)
    cancel_response = await api_client.delete(f"/messages/{message_id}")

    # May succeed or fail depending on timing
    assert cancel_response.status_code in [200, 409]


@pytest.mark.asyncio
async def test_get_queue_summary(api_client):
    """Test getting queue summary"""
    response = await api_client.get("/queue")

    assert response.status_code == 200
    data = response.json()
    assert "total_queued" in data
    assert "total_processing" in data
    assert "total_completed" in data
    assert "queued_messages" in data


@pytest.mark.asyncio
async def test_message_validation(api_client):
    """Test message validation"""
    # Empty message should fail
    response = await api_client.post(
        "/messages",
        json={"message": ""}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_priority_validation(api_client):
    """Test priority validation"""
    # Invalid priority should fail
    response = await api_client.post(
        "/messages",
        json={
            "message": "Test",
            "priority": "invalid"
        }
    )

    assert response.status_code == 422
