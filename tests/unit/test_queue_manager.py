import pytest
from app.queue_manager import QueueManager
from app.models import Priority, MessageState


@pytest.mark.asyncio
async def test_enqueue_message():
    """Test enqueueing a message"""
    qm = QueueManager()

    message = await qm.enqueue("Test message", thread_id="thread-1", priority=Priority.NORMAL)

    assert message.id is not None
    assert message.user_message == "Test message"
    assert message.priority == Priority.NORMAL
    assert message.state == MessageState.QUEUED
    assert message.thread_id == "thread-1"


@pytest.mark.asyncio
async def test_dequeue_message():
    """Test dequeueing a message"""
    qm = QueueManager()

    # Enqueue a message with thread_id
    thread_id = "thread-1"
    enqueued = await qm.enqueue("Test message", thread_id=thread_id)

    # Dequeue the message from the thread
    dequeued = await qm.dequeue(thread_id)

    assert dequeued is not None
    assert dequeued.id == enqueued.id
    assert dequeued.state == MessageState.PROCESSING


@pytest.mark.asyncio
async def test_priority_ordering():
    """Test that high priority messages are dequeued first within a thread"""
    qm = QueueManager()

    thread_id = "thread-1"
    
    # Enqueue messages in different order within the same thread
    low = await qm.enqueue("Low priority", thread_id=thread_id, priority=Priority.LOW)
    high = await qm.enqueue("High priority", thread_id=thread_id, priority=Priority.HIGH)
    normal = await qm.enqueue("Normal priority", thread_id=thread_id, priority=Priority.NORMAL)

    # Dequeue should return high priority first
    first = await qm.dequeue(thread_id)
    assert first.id == high.id

    second = await qm.dequeue(thread_id)
    assert second.id == normal.id

    third = await qm.dequeue(thread_id)
    assert third.id == low.id


@pytest.mark.asyncio
async def test_fifo_within_priority():
    """Test FIFO ordering within same priority in a thread"""
    qm = QueueManager()

    thread_id = "thread-1"
    
    # Enqueue multiple normal priority messages in the same thread
    msg1 = await qm.enqueue("First", thread_id=thread_id, priority=Priority.NORMAL)
    msg2 = await qm.enqueue("Second", thread_id=thread_id, priority=Priority.NORMAL)
    msg3 = await qm.enqueue("Third", thread_id=thread_id, priority=Priority.NORMAL)

    # Should dequeue in FIFO order
    first = await qm.dequeue(thread_id)
    assert first.id == msg1.id

    second = await qm.dequeue(thread_id)
    assert second.id == msg2.id

    third = await qm.dequeue(thread_id)
    assert third.id == msg3.id


@pytest.mark.asyncio
async def test_update_state():
    """Test updating message state"""
    qm = QueueManager()

    message = await qm.enqueue("Test", thread_id="thread-1")

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

    message = await qm.enqueue("Test", thread_id="thread-1")

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

    message = await qm.enqueue("Test", thread_id="thread-1")

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

    message = await qm.enqueue("Test", thread_id="thread-1")

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

    message = await qm.enqueue("Test message", thread_id="thread-1")

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

    message = await qm.enqueue("Test", thread_id="thread-1")

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

    message = await qm.enqueue("Test", thread_id="thread-1")

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
    await qm.enqueue("Queued 1", thread_id="thread-1")
    await qm.enqueue("Queued 2", thread_id="thread-1")

    msg3 = await qm.enqueue("Processing", thread_id="thread-2")
    await qm.update_state(msg3.id, MessageState.PROCESSING)

    msg4 = await qm.enqueue("Completed", thread_id="thread-3")
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

    thread_id = "thread-1"
    
    msg1 = await qm.enqueue("Message 1", thread_id=thread_id)
    msg2 = await qm.enqueue("Message 2", thread_id=thread_id)

    # Cancel first message
    await qm.cancel_message(msg1.id)

    # Dequeue should skip cancelled and return None (since cancelled is skipped)
    dequeued1 = await qm.dequeue(thread_id)
    assert dequeued1 is None  # First dequeue gets the cancelled message and returns None
    
    # Second dequeue should return the second message
    dequeued2 = await qm.dequeue(thread_id)
    assert dequeued2 is not None
    assert dequeued2.id == msg2.id


@pytest.mark.asyncio
async def test_thread_independence():
    """Test that threads have independent queues"""
    qm = QueueManager()

    thread1 = "thread-1"
    thread2 = "thread-2"
    
    # Enqueue messages to different threads
    msg1_t1 = await qm.enqueue("Thread 1 - Message 1", thread_id=thread1)
    msg1_t2 = await qm.enqueue("Thread 2 - Message 1", thread_id=thread2)
    msg2_t1 = await qm.enqueue("Thread 1 - Message 2", thread_id=thread1)
    msg2_t2 = await qm.enqueue("Thread 2 - Message 2", thread_id=thread2)

    # Verify threads are tracked as active
    active_threads = qm.get_active_threads()
    assert thread1 in active_threads
    assert thread2 in active_threads

    # Dequeue from thread 1
    dequeued = await qm.dequeue(thread1)
    assert dequeued is not None
    assert dequeued.id == msg1_t1.id
    assert dequeued.thread_id == thread1

    # Thread 2 should still have its messages
    assert qm.has_messages(thread2)
    
    # Dequeue from thread 2
    dequeued = await qm.dequeue(thread2)
    assert dequeued is not None
    assert dequeued.id == msg1_t2.id
    assert dequeued.thread_id == thread2

    # Both threads should still have one message
    assert qm.has_messages(thread1)
    assert qm.has_messages(thread2)


@pytest.mark.asyncio
async def test_get_active_threads():
    """Test getting active threads with pending messages"""
    qm = QueueManager()

    thread1 = "thread-1"
    thread2 = "thread-2"
    thread3 = "thread-3"
    
    # Initially no active threads
    assert len(qm.get_active_threads()) == 0

    # Add messages to different threads
    await qm.enqueue("Message 1", thread_id=thread1)
    await qm.enqueue("Message 2", thread_id=thread2)
    await qm.enqueue("Message 3", thread_id=thread3)

    # All threads should be active
    active = qm.get_active_threads()
    assert len(active) == 3
    assert thread1 in active
    assert thread2 in active
    assert thread3 in active

    # Dequeue from thread 1 (empty the queue)
    await qm.dequeue(thread1)
    
    # Thread 1 should no longer be active
    active = qm.get_active_threads()
    assert len(active) == 2
    assert thread1 not in active
    assert thread2 in active
    assert thread3 in active
