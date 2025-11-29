from datetime import datetime
from enum import Enum
from typing import Optional, Dict
from pydantic import BaseModel, Field
import uuid


class MessageState(str, Enum):
    """Message processing states"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Priority(str, Enum):
    """Message priority levels"""
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


# Priority to integer mapping for queue ordering (lower number = higher priority)
PRIORITY_MAP = {
    Priority.HIGH: 1,
    Priority.NORMAL: 2,
    Priority.LOW: 3,
}


class QueuedMessage(BaseModel):
    """Internal representation of a queued message"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_message: str
    priority: Priority = Priority.NORMAL
    state: MessageState = MessageState.QUEUED
    thread_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None
    chunks: list[str] = Field(default_factory=list)

    class Config:
        use_enum_values = False


class MessageSubmitRequest(BaseModel):
    """Request model for submitting a new message"""
    message: str = Field(..., min_length=1, max_length=10000)
    priority: Priority = Priority.NORMAL
    thread_id: Optional[str] = Field(None, max_length=255)


class MessageSubmitResponse(BaseModel):
    """Response model for message submission"""
    message_id: str
    state: MessageState
    queue_position: Optional[int] = None
    created_at: datetime
    thread_id: Optional[str] = None


class MessageStatusResponse(BaseModel):
    """Response model for message status query"""
    message_id: str
    state: MessageState
    user_message: str
    priority: Priority
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None
    queue_position: Optional[int] = None
    thread_id: Optional[str] = None


class QueueSummaryResponse(BaseModel):
    """Response model for queue summary"""
    total_queued: int
    total_processing: int
    total_completed: int
    total_failed: int
    total_cancelled: int
    queued_messages: list[dict]
    current_processing: Optional[dict] = None


class SSEEvent(BaseModel):
    """Model for Server-Sent Events"""
    event: Optional[str] = None
    data: dict

    def format(self) -> str:
        """Format as SSE event string"""
        lines = []
        if self.event:
            lines.append(f"event: {self.event}")

        # Convert data to JSON string
        import json
        data_str = json.dumps(self.data)
        lines.append(f"data: {data_str}")
        lines.append("")  # Empty line to end event

        return "\n".join(lines) + "\n"


class ThreadMetadata(BaseModel):
    """Thread-level metadata"""
    thread_id: str
    message_count: int
    created_at: datetime
    last_activity: datetime
    states: Dict[MessageState, int]


class ThreadSummary(BaseModel):
    """Summary info for listing threads"""
    thread_id: str
    message_count: int
    created_at: datetime
    last_activity: datetime
    last_message_preview: Optional[str] = None


class ThreadMessagesResponse(BaseModel):
    """Response model for thread message queries"""
    thread_id: str
    total_messages: int
    messages: list[MessageStatusResponse]
