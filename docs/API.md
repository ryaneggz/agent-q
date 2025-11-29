# API Reference

## 1. Submit Message

Submit a new message to the queue.

**Endpoint:** `POST /messages`

**Request:**
```bash
curl -X POST http://localhost:8000/messages \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the capital of France?",
    "priority": "normal",
    "thread_id": "a2e40f10-9f5a-4a54-9fb4-3b9f861fc2c0"
  }'
```

**Parameters:**
- `message` (string, required): The user's input message.
- `priority` (string, optional): `high`, `normal` (default), or `low`.
- `thread_id` (string, optional): ID to group messages into a conversation thread. Max 255 chars.

**Response (202 Accepted):**
```json
{
    "message_id": "550e8400-e29b-41d4-a716-446655440000",
    "state": "queued",
    "queue_position": 0,
    "created_at": "2024-01-15T10:30:00.000Z",
    "thread_id": "a2e40f10-9f5a-4a54-9fb4-3b9f861fc2c0"
}
```

---

## 2. Get Message Status

Check the status of a specific message.

**Endpoint:** `GET /messages/{message_id}/status`

**Response (200 OK):**
```json
{
    "message_id": "550e8400-e29b-41d4-a716-446655440000",
    "state": "completed",
    "user_message": "What is the capital of France?",
    "priority": "normal",
    "created_at": "2024-01-15T10:30:00.000Z",
    "started_at": "2024-01-15T10:30:05.000Z",
    "completed_at": "2024-01-15T10:30:15.000Z",
    "result": "The capital of France is Paris.",
    "error": null,
    "queue_position": null,
    "thread_id": "a2e40f10-9f5a-4a54-9fb4-3b9f861fc2c0"
}
```

**Message States:**
- `queued`: Waiting in the queue.
- `processing`: Currently being processed by the agent.
- `completed`: Successfully processed.
- `failed`: Processing failed with an error.
- `cancelled`: Cancelled by user before processing started.

---

## 3. Stream Message Response

Stream the agent's response in real-time using Server-Sent Events (SSE).

**Endpoint:** `GET /messages/{message_id}/stream`

**Response (Text/Event-Stream):**
```
event: waiting
data: {"state": "queued", "position": 2, "message": "Waiting in queue"}

event: chunk
data: {"type": "content", "chunk": "The capital ", "index": 0}

event: chunk
data: {"type": "content", "chunk": "of France is Paris.", "index": 1}

event: done
data: {"state": "completed", "result": "The capital of France is Paris.", "completed_at": "2024-01-15T10:30:15.000Z"}
```

---

## 4. Cancel Message

Cancel a queued message. Only works if the message is in `queued` state.

**Endpoint:** `DELETE /messages/{message_id}`

**Response (200 OK):**
```json
{
    "message": "Message cancelled successfully",
    "message_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Error (409 Conflict):** If message is already processing.

---

## 5. Get Queue Summary

View the current state of the queue (admin/debug).

**Endpoint:** `GET /queue`

**Response (200 OK):**
```json
{
    "total_queued": 5,
    "total_processing": 1,
    "total_completed": 23,
    "total_failed": 2,
    "total_cancelled": 1,
    "queued_messages": [...],
    "current_processing": {...}
}
```

---

## 6. List Threads

Retrieve active threads sorted by last activity.

**Endpoint:** `GET /threads`

**Response (200 OK):**
```json
[
    {
        "thread_id": "a2e40f10-9f5a-4a54-9fb4-3b9f861fc2c0",
        "message_count": 2,
        "created_at": "2024-01-15T10:30:00.000Z",
        "last_activity": "2024-01-15T10:31:10.000Z",
        "last_message_preview": "Follow-up: What's its population?"
    }
]
```

---

## 7. Get Thread Metadata

Get detailed metadata for a specific thread.

**Endpoint:** `GET /threads/{thread_id}`

**Response (200 OK):**
```json
{
    "thread_id": "...",
    "message_count": 2,
    "created_at": "...",
    "last_activity": "...",
    "states": {
        "queued": 0,
        "processing": 0,
        "completed": 2,
        "failed": 0,
        "cancelled": 0
    }
}
```

---

## 8. Get Thread Messages

Get all messages in a thread.

**Endpoint:** `GET /threads/{thread_id}/messages`

**Response (200 OK):**
```json
{
    "thread_id": "...",
    "total_messages": 2,
    "messages": [...]
}
```

---

## 9. Health Check

**Endpoint:** `GET /health`

**Response (200 OK):**
```json
{"status": "ok"}
```

