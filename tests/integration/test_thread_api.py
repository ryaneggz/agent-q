import uuid

import pytest


@pytest.mark.asyncio
async def test_thread_lifecycle_endpoints(api_client):
    thread_id = f"thread-{uuid.uuid4()}"

    # Submit first message in thread
    first_resp = await api_client.post(
        "/messages",
        json={"message": "First threaded message", "thread_id": thread_id},
    )
    assert first_resp.status_code == 202
    first_data = first_resp.json()
    assert first_data["thread_id"] == thread_id

    # Submit second message in same thread
    second_resp = await api_client.post(
        "/messages",
        json={"message": "Second threaded message", "thread_id": thread_id},
    )
    assert second_resp.status_code == 202
    second_data = second_resp.json()
    assert second_data["thread_id"] == thread_id

    # List threads
    threads_resp = await api_client.get("/threads")
    assert threads_resp.status_code == 200
    threads_data = threads_resp.json()
    assert any(thread["thread_id"] == thread_id for thread in threads_data)

    # Get thread metadata
    metadata_resp = await api_client.get(f"/threads/{thread_id}")
    assert metadata_resp.status_code == 200
    metadata = metadata_resp.json()
    assert metadata["thread_id"] == thread_id
    assert metadata["message_count"] >= 2

    # Get thread messages
    messages_resp = await api_client.get(f"/threads/{thread_id}/messages")
    assert messages_resp.status_code == 200
    messages = messages_resp.json()
    assert messages["thread_id"] == thread_id
    assert messages["total_messages"] == 2
    returned_ids = [msg["message_id"] for msg in messages["messages"]]
    assert first_data["message_id"] in returned_ids
    assert second_data["message_id"] in returned_ids


@pytest.mark.asyncio
async def test_thread_not_found_returns_404(api_client):
    missing_id = "non-existent-thread"

    resp_meta = await api_client.get(f"/threads/{missing_id}")
    assert resp_meta.status_code == 404

    resp_messages = await api_client.get(f"/threads/{missing_id}/messages")
    assert resp_messages.status_code == 404


@pytest.mark.asyncio
async def test_backward_compatibility_without_thread(api_client):
    submit_resp = await api_client.post("/messages", json={"message": "Legacy message"})
    assert submit_resp.status_code == 202
    data = submit_resp.json()
    assert data["thread_id"] is None

    status_resp = await api_client.get(f"/messages/{data['message_id']}/status")
    assert status_resp.status_code == 200
    status = status_resp.json()
    assert "thread_id" in status
    assert status["thread_id"] is None


@pytest.mark.asyncio
async def test_thread_id_validation(api_client):
    too_long_id = "x" * 300
    resp = await api_client.post(
        "/messages",
        json={"message": "Invalid thread id", "thread_id": too_long_id},
    )

    assert resp.status_code == 422
