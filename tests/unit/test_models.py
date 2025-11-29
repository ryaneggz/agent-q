import pytest
from datetime import datetime
from shinzo.models import (
    MessageState,
    Priority,
    QueuedMessage,
    MessageSubmitRequest,
    SSEEvent,
    PRIORITY_MAP,
)


def test_message_state_enum():
    """Test MessageState enum values"""
    assert MessageState.QUEUED == "queued"
    assert MessageState.PROCESSING == "processing"
    assert MessageState.COMPLETED == "completed"
    assert MessageState.FAILED == "failed"
    assert MessageState.CANCELLED == "cancelled"


def test_priority_enum():
    """Test Priority enum values"""
    assert Priority.HIGH == "high"
    assert Priority.NORMAL == "normal"
    assert Priority.LOW == "low"


def test_priority_map():
    """Test priority ordering"""
    assert PRIORITY_MAP[Priority.HIGH] < PRIORITY_MAP[Priority.NORMAL]
    assert PRIORITY_MAP[Priority.NORMAL] < PRIORITY_MAP[Priority.LOW]


def test_queued_message_creation():
    """Test QueuedMessage creation with defaults"""
    message = QueuedMessage(user_message="Test message")

    assert message.id is not None
    assert message.user_message == "Test message"
    assert message.priority == Priority.NORMAL
    assert message.state == MessageState.QUEUED
    assert isinstance(message.created_at, datetime)
    assert message.started_at is None
    assert message.completed_at is None
    assert message.result is None
    assert message.error is None
    assert message.chunks == []


def test_queued_message_with_priority():
    """Test QueuedMessage creation with high priority"""
    message = QueuedMessage(
        user_message="Urgent message",
        priority=Priority.HIGH
    )

    assert message.priority == Priority.HIGH
    assert message.state == MessageState.QUEUED


def test_message_submit_request_validation():
    """Test MessageSubmitRequest validation"""
    request = MessageSubmitRequest(
        message="Test message",
        priority=Priority.NORMAL
    )

    assert request.message == "Test message"
    assert request.priority == Priority.NORMAL


def test_message_submit_request_default_priority():
    """Test MessageSubmitRequest with default priority"""
    request = MessageSubmitRequest(message="Test")

    assert request.priority == Priority.NORMAL


def test_sse_event_format():
    """Test SSE event formatting"""
    event = SSEEvent(
        event="test",
        data={"message": "hello", "count": 42}
    )

    formatted = event.format()

    assert "event: test" in formatted
    assert '"message": "hello"' in formatted or '"message":"hello"' in formatted
    assert '"count": 42' in formatted or '"count":42' in formatted
    assert formatted.endswith("\n")


def test_sse_event_without_event_type():
    """Test SSE event without event type"""
    event = SSEEvent(
        data={"status": "ok"}
    )

    formatted = event.format()

    assert "event:" not in formatted or formatted.count("event:") == 0 or "event: None" not in formatted
    assert "data:" in formatted
