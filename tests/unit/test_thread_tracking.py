import asyncio

import pytest

from app.queue_manager import QueueManager
from app.models import MessageState, Priority


@pytest.mark.asyncio
async def test_thread_created_on_first_message():
    qm = QueueManager()
    thread_id = "thread-123"

    await qm.enqueue("Hello", priority=Priority.NORMAL, thread_id=thread_id)

    metadata = await qm.get_thread_metadata(thread_id)
    assert metadata is not None
    assert metadata.thread_id == thread_id
    assert metadata.message_count == 1
    assert metadata.states[MessageState.QUEUED] == 1


@pytest.mark.asyncio
async def test_multiple_messages_same_thread():
    qm = QueueManager()
    thread_id = "thread-abc"

    await qm.enqueue("First", thread_id=thread_id)
    await qm.enqueue("Second", thread_id=thread_id)

    metadata = await qm.get_thread_metadata(thread_id)
    assert metadata.message_count == 2

    messages = await qm.get_thread_messages(thread_id)
    assert len(messages) == 2
    assert [msg.user_message for msg in messages] == ["First", "Second"]


@pytest.mark.asyncio
async def test_thread_metadata_updates_on_state_change():
    qm = QueueManager()
    thread_id = "thread-state"

    message = await qm.enqueue("Process me", thread_id=thread_id)
    await qm.update_state(message.id, MessageState.PROCESSING)
    await qm.update_state(message.id, MessageState.COMPLETED)

    metadata = await qm.get_thread_metadata(thread_id)
    assert metadata.states[MessageState.QUEUED] == 0
    assert metadata.states[MessageState.PROCESSING] == 0
    assert metadata.states[MessageState.COMPLETED] == 1


@pytest.mark.asyncio
async def test_get_thread_messages_chronological_order():
    qm = QueueManager()
    thread_id = "thread-order"

    first = await qm.enqueue("First", thread_id=thread_id)
    await asyncio.sleep(0.01)
    second = await qm.enqueue("Second", thread_id=thread_id)

    messages = await qm.get_thread_messages(thread_id)
    assert [msg.id for msg in messages] == [first.id, second.id]


@pytest.mark.asyncio
async def test_list_threads_sorted_by_activity():
    qm = QueueManager()

    first_thread = "thread-one"
    second_thread = "thread-two"

    msg1 = await qm.enqueue("Hello", thread_id=first_thread)
    msg2 = await qm.enqueue("Hi", thread_id=second_thread)

    await qm.update_state(msg2.id, MessageState.PROCESSING)

    summaries = await qm.list_threads()
    assert summaries[0].thread_id == second_thread
    assert summaries[1].thread_id == first_thread


@pytest.mark.asyncio
async def test_thread_messages_handle_missing_entries():
    qm = QueueManager()
    thread_id = "thread-missing"

    message = await qm.enqueue("To be deleted", thread_id=thread_id)

    # Simulate message removal
    async with qm._lock:  # type: ignore[attr-defined]
        del qm._messages[message.id]  # type: ignore[attr-defined]

    messages = await qm.get_thread_messages(thread_id)
    assert messages == []


@pytest.mark.asyncio
async def test_cancelling_threaded_message_updates_states():
    qm = QueueManager()
    thread_id = "thread-cancel"

    message = await qm.enqueue("Cancel me", thread_id=thread_id)
    await qm.cancel_message(message.id)

    metadata = await qm.get_thread_metadata(thread_id)
    assert metadata.states[MessageState.CANCELLED] == 1
    assert metadata.message_count == 1


@pytest.mark.asyncio
async def test_thread_scaling_handles_many_threads():
    qm = QueueManager()

    for idx in range(100):
        thread_id = f"thread-{idx}"
        for _ in range(10):
            await qm.enqueue(f"Message {idx}", thread_id=thread_id)

    summaries = await qm.list_threads()
    assert len(summaries) == 100

    sample_thread = summaries[0].thread_id
    metadata = await qm.get_thread_metadata(sample_thread)
    assert metadata is not None
    assert metadata.message_count == 10

    messages = await qm.get_thread_messages(sample_thread)
    assert len(messages) == 10

