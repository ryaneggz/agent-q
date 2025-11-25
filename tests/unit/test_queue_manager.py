import pytest
from app.queue_manager import QueueManager
from app.models import Priority, MessageState


@pytest.mark.asyncio
async def test_enqueue_message():
    """Test enqueueing a message"""
    qm = QueueManager()

    message = await qm.enqueue("Test message", Priority.NORMAL)

    assert message.id is not None
    assert message.user_message == "Test message"
    assert message.priority == Priority.NORMAL
    assert message.state == MessageState.QUEUED


@pytest.mark.asyncio
async def test_dequeue_message():
    """Test dequeueing a message"""
    qm = QueueManager()

    # Enqueue a message
    enqueued = await qm.enqueue("Test message")

    # Dequeue the message
    dequeued = await qm.dequeue()

    assert dequeued is not None
    assert dequeued.id == enqueued.id
    assert dequeued.state == MessageState.PROCESSING


@pytest.mark.asyncio
async def test_priority_ordering():
    """Test that high priority messages are dequeued first"""
    qm = QueueManager()

    # Enqueue messages in different order
    low = await qm.enqueue("Low priority", Priority.LOW)
    high = await qm.enqueue("High priority", Priority.HIGH)
    normal = await qm.enqueue("Normal priority", Priority.NORMAL)

    # Dequeue should return high priority first
    first = await qm.dequeue()
    assert first.id == high.id

    second = await qm.dequeue()
    assert second.id == normal.id

    third = await qm.dequeue()
    assert third.id == low.id


@pytest.mark.asyncio
async def test_fifo_within_priority():
    """Test FIFO ordering within same priority"""
    qm = QueueManager()

    # Enqueue multiple normal priority messages
    msg1 = await qm.enqueue("First", Priority.NORMAL)
    msg2 = await qm.enqueue("Second", Priority.NORMAL)
    msg3 = await qm.enqueue("Third", Priority.NORMAL)

    # Should dequeue in FIFO order
    first = await qm.dequeue()
    assert first.id == msg1.id

    second = await qm.dequeue()
    assert second.id == msg2.id

    third = await qm.dequeue()
    assert third.id == msg3.id


@pytest.mark.asyncio
async def test_update_state():
    """Test updating message state"""
    qm = QueueManager()

    message = await qm.enqueue("Test")

    # Update to processing
    success = await qm.update_state(message.id, MessageState.PROCESSING)
    assert success is True

    # Verify state changed
    updated = await qm.get_message(message.id)
    assert updated.state == MessageState.PROCESSING
    assert updated.started_at is not None


@pytest.mark.asyncio
async def test_invalid_state_transition():
    """Test that invalid state transitions are rejected"""
    qm = QueueManager()

    message = await qm.enqueue("Test")

    # Cannot go from QUEUED to COMPLETED directly
    success = await qm.update_state(message.id, MessageState.COMPLETED)
    assert success is False

    # State should remain QUEUED
    updated = await qm.get_message(message.id)
    assert updated.state == MessageState.QUEUED


@pytest.mark.asyncio
async def test_cancel_queued_message():
    """Test cancelling a queued message"""
    qm = QueueManager()

    message = await qm.enqueue("Test")

    # Cancel the message
    success, error = await qm.cancel_message(message.id)
    assert success is True
    assert error is None

    # Verify state is cancelled
    updated = await qm.get_message(message.id)
    assert updated.state == MessageState.CANCELLED
    assert updated.completed_at is not None


@pytest.mark.asyncio
async def test_cannot_cancel_processing_message():
    """Test that processing messages cannot be cancelled"""
    qm = QueueManager()

    message = await qm.enqueue("Test")

    # Update to processing
    await qm.update_state(message.id, MessageState.PROCESSING)

    # Try to cancel
    success, error = await qm.cancel_message(message.id)
    assert success is False
    assert "Cannot cancel" in error


@pytest.mark.asyncio
async def test_get_message():
    """Test retrieving a message by ID"""
    qm = QueueManager()

    message = await qm.enqueue("Test message")

    # Get message
    retrieved = await qm.get_message(message.id)
    assert retrieved is not None
    assert retrieved.id == message.id
    assert retrieved.user_message == "Test message"


@pytest.mark.asyncio
async def test_get_nonexistent_message():
    """Test retrieving a non-existent message"""
    qm = QueueManager()

    retrieved = await qm.get_message("nonexistent-id")
    assert retrieved is None


@pytest.mark.asyncio
async def test_set_result():
    """Test setting a message result"""
    qm = QueueManager()

    message = await qm.enqueue("Test")

    # Set result
    success = await qm.set_result(message.id, "Agent response")
    assert success is True

    # Verify result
    updated = await qm.get_message(message.id)
    assert updated.result == "Agent response"


@pytest.mark.asyncio
async def test_add_chunk():
    """Test adding streaming chunks"""
    qm = QueueManager()

    message = await qm.enqueue("Test")

    # Add chunks
    await qm.add_chunk(message.id, "chunk1")
    await qm.add_chunk(message.id, "chunk2")

    # Verify chunks
    updated = await qm.get_message(message.id)
    assert len(updated.chunks) == 2
    assert updated.chunks[0] == "chunk1"
    assert updated.chunks[1] == "chunk2"


@pytest.mark.asyncio
async def test_get_queue_summary():
    """Test getting queue summary"""
    qm = QueueManager()

    # Enqueue various messages
    await qm.enqueue("Queued 1")
    await qm.enqueue("Queued 2")

    msg3 = await qm.enqueue("Processing")
    await qm.update_state(msg3.id, MessageState.PROCESSING)

    msg4 = await qm.enqueue("Completed")
    await qm.update_state(msg4.id, MessageState.PROCESSING)
    await qm.update_state(msg4.id, MessageState.COMPLETED)

    # Get summary
    summary = await qm.get_queue_summary()

    assert summary.total_queued == 2
    assert summary.total_processing == 1
    assert summary.total_completed == 1
    assert len(summary.queued_messages) == 2


@pytest.mark.asyncio
async def test_dequeue_skips_cancelled():
    """Test that dequeue skips cancelled messages"""
    qm = QueueManager()

    msg1 = await qm.enqueue("Message 1")
    msg2 = await qm.enqueue("Message 2")

    # Cancel first message
    await qm.cancel_message(msg1.id)

    # Dequeue should skip cancelled and return second
    dequeued = await qm.dequeue()
    assert dequeued is None or dequeued.id == msg2.id
