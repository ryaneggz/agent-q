# Agent Queue System

AI Agent Queue System with FastAPI and LangGraph - A production-ready message queue for processing AI agent requests with streaming support.

## Features

- **Priority Queue**: Process messages based on priority (high, normal, low) with FIFO ordering within each priority level
- **Sequential Processing**: One message at a time to ensure consistent agent behavior
- **Server-Sent Events (SSE)**: Real-time streaming of agent responses
- **Queue Management**: Full CRUD operations for messages with state tracking
- **Conversation Threads**: Optional `thread_id` parameter groups related messages with metadata and history endpoints
- **Graceful Lifecycle**: Proper startup/shutdown with worker management
- **Async-First**: Built with asyncio for high concurrency
- **Type-Safe**: Fully typed with Pydantic models

## Architecture

```
┌─────────────────┐
│  FastAPI Layer  │ (HTTP endpoints, SSE streaming)
└────────┬────────┘
         │
┌────────▼────────┐
│  Queue Manager  │ (In-memory queue, priority, status tracking)
└────────┬────────┘
         │
┌────────▼────────┐
│ Agent Processor │ (LangGraph integration, one-at-a-time processing)
└─────────────────┘
```

## Installation

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd agent-queue-system
```

2. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Install dependencies using uv:
```bash
uv sync
```

Or using pip:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

5. Configure your environment variables in `.env`:
```env
OPENAI_API_KEY=your-openai-api-key-here
MODEL_NAME=gpt-4
MAX_QUEUE_SIZE=1000
PROCESSING_TIMEOUT=60
KEEPALIVE_INTERVAL=30
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

## Usage

### Running the Server

Using uv:
```bash
uv run python -m app.main
```

Or with uvicorn directly:
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will start on `http://localhost:8000`.

### API Endpoints

#### 1. Submit Message

Submit a new message to the queue:

```bash
curl -X POST http://localhost:8000/messages \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the capital of France?",
    "priority": "normal",
    "thread_id": "a2e40f10-9f5a-4a54-9fb4-3b9f861fc2c0"
  }'
```

Response:
```json
{
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "queued",
  "queue_position": 0,
  "created_at": "2024-01-15T10:30:00.000Z",
  "thread_id": "a2e40f10-9f5a-4a54-9fb4-3b9f861fc2c0"
}
```

Priority options: `high`, `normal` (default), `low`

Threading notes:
- `thread_id` is optional; omit it for standalone messages or reuse an existing value to continue a conversation.
- IDs can be any string up to 255 characters (UUID recommended to avoid collisions).
- The API echoes `thread_id` in submit/status responses to make correlation easy.

#### 2. Get Message Status

Check the status of a message:

```bash
curl http://localhost:8000/messages/{message_id}/status
```

Response:
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

Message states: `queued`, `processing`, `completed`, `failed`, `cancelled`

#### 3. Stream Message Response (SSE)

Stream the agent's response in real-time:

```bash
curl -N http://localhost:8000/messages/{message_id}/stream
```

Example SSE events:
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

#### 4. Cancel Message

Cancel a queued message (only works if not yet processing):

```bash
curl -X DELETE http://localhost:8000/messages/{message_id}
```

Response:
```json
{
  "message": "Message cancelled successfully",
  "message_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### 5. Get Queue Summary

View the current queue state (admin/debug):

```bash
curl http://localhost:8000/queue
```

Response:
```json
{
  "total_queued": 5,
  "total_processing": 1,
  "total_completed": 23,
  "total_failed": 2,
  "total_cancelled": 1,
  "queued_messages": [
    {
      "id": "...",
      "priority": "high",
      "created_at": "2024-01-15T10:30:00.000Z",
      "user_message": "Urgent request..."
    }
  ],
  "current_processing": {
    "id": "...",
    "priority": "normal",
    "started_at": "2024-01-15T10:29:55.000Z",
    "user_message": "Processing this now..."
  }
}
```

#### 6. Health Check

```bash
curl http://localhost:8000/health
```

#### 7. List Threads

Retrieve every active thread with summary metadata sorted by last activity:

```bash
curl http://localhost:8000/threads
```

Response:
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

#### 8. Get Thread Metadata

```bash
curl http://localhost:8000/threads/{thread_id}
```

Response:
```json
{
  "thread_id": "a2e40f10-9f5a-4a54-9fb4-3b9f861fc2c0",
  "message_count": 2,
  "created_at": "2024-01-15T10:30:00.000Z",
  "last_activity": "2024-01-15T10:31:10.000Z",
  "states": {
    "queued": 0,
    "processing": 0,
    "completed": 2,
    "failed": 0,
    "cancelled": 0
  }
}
```

#### 9. Get Thread Messages

```bash
curl http://localhost:8000/threads/{thread_id}/messages
```

Response:
```json
{
  "thread_id": "a2e40f10-9f5a-4a54-9fb4-3b9f861fc2c0",
  "total_messages": 2,
  "messages": [
    {
      "message_id": "550e8400-e29b-41d4-a716-446655440000",
      "state": "completed",
      "user_message": "Threaded question: What is the capital of France?",
      "priority": "normal",
      "created_at": "2024-01-15T10:30:00.000Z",
      "started_at": "2024-01-15T10:30:05.000Z",
      "completed_at": "2024-01-15T10:30:15.000Z",
      "result": "The capital of France is Paris.",
      "error": null,
      "queue_position": null,
      "thread_id": "a2e40f10-9f5a-4a54-9fb4-3b9f861fc2c0"
    }
  ]
}
```

### Threaded Conversation Example

```bash
# 1) Submit first message with a client-generated thread_id
THREAD_ID=$(uuidgen)
curl -X POST http://localhost:8000/messages \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Threaded question: What is the capital of France?\", \"priority\": \"normal\", \"thread_id\": \"$THREAD_ID\"}"

# 2) Submit follow-up in the same thread
curl -X POST http://localhost:8000/messages \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Follow-up: What's its population?\", \"priority\": \"normal\", \"thread_id\": \"$THREAD_ID\"}"

# 3) Inspect all messages for the thread
curl http://localhost:8000/threads/$THREAD_ID/messages | jq
```

Best practices:
- Reuse the same `thread_id` for every turn of the conversation.
- Store the ID client-side (recommend UUIDs) so you can resume the thread later.
- Thread metadata is updated automatically as each message changes state.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for LangGraph | (required) |
| `MODEL_NAME` | LLM model name | `gpt-4` |
| `MAX_QUEUE_SIZE` | Maximum messages in queue | `1000` |
| `PROCESSING_TIMEOUT` | Max processing time per message (seconds) | `60` |
| `KEEPALIVE_INTERVAL` | SSE keepalive interval (seconds) | `30` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Development

### Running Tests

Run all tests:
```bash
uv run pytest
```

Run with coverage:
```bash
uv run pytest --cov=app --cov-report=html
```

Run specific test files:
```bash
uv run pytest tests/unit/test_models.py
uv run pytest tests/unit/test_queue_manager.py
uv run pytest tests/integration/test_api.py
```

### Code Quality

Format code:
```bash
uv run black app tests
```

Lint code:
```bash
uv run ruff check app tests
```

## Project Structure

```
agent-queue-system/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── models.py            # Pydantic models
│   ├── config.py            # Configuration settings
│   ├── queue_manager.py     # Queue management logic
│   ├── agent_processor.py   # LangGraph agent integration
│   ├── worker.py            # Background worker task
│   └── api/
│       ├── __init__.py
│       ├── routes.py        # REST API endpoints
│       ├── threads.py       # Thread query endpoints
│       └── streaming.py     # SSE streaming endpoint
├── tests/
│   ├── unit/
│   │   ├── test_models.py
│   │   ├── test_queue_manager.py
│   │   └── test_thread_tracking.py
│   └── integration/
│       ├── test_api.py
│       └── test_thread_api.py
├── config/                  # Configuration files
├── .env.example             # Example environment variables
├── pyproject.toml           # Poetry dependencies
├── pytest.ini               # Pytest configuration
└── README.md
```

## Limitations

### Current MVP Limitations

- **In-Memory Queue**: Queue is not persisted; messages are lost on restart
- **Single Worker**: Only one message processes at a time
- **No Authentication**: Endpoints are not authenticated
- **No Rate Limiting**: No rate limiting per user/IP
- **No Retry Logic**: Failed messages are not automatically retried
- **Thread Pagination**: Thread listing/message endpoints return full in-memory results (no pagination or TTL yet)

### Future Enhancements

- Persistent queue backend (Redis, PostgreSQL)
- Multi-worker support for parallel processing
- Authentication & authorization
- Rate limiting and quotas
- Message retry with exponential backoff
- Dead-letter queue for failed messages
- Metrics and monitoring integration
- WebSocket alternative to SSE

## Troubleshooting

### Common Issues

**Server won't start**
- Check that port 8000 is not already in use
- Verify all environment variables are set correctly
- Ensure OpenAI API key is valid

**Messages stuck in queue**
- Check worker is running: look for "Worker started" in logs
- Verify agent initialization succeeded
- Check processing timeout is not too short

**SSE connection drops**
- Increase `KEEPALIVE_INTERVAL` if on slow connection
- Check for reverse proxy timeout settings
- Verify client supports SSE

**Agent errors**
- Check OpenAI API key is valid and has credits
- Verify model name is correct
- Check agent initialization logs for errors

### Logging

Logs are written to stdout with configurable level. Example:
```
2024-01-15 10:30:00 - app.queue_manager - INFO - Message enqueued: id=..., priority=normal
2024-01-15 10:30:05 - app.worker - INFO - Worker processing message: id=...
2024-01-15 10:30:15 - app.agent_processor - INFO - Message processed successfully: id=...
```

Set `LOG_LEVEL=DEBUG` for verbose output.

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Client Examples

### TypeScript Demo

A comprehensive TypeScript client demo is available that demonstrates all API endpoints with detailed console logging.

**Location:** `examples/typescript-client/`

**Quick start:**
```bash
cd examples/typescript-client
npm install
npm run demo
```

**Prerequisites:**
- Node.js 18+ (for native fetch API)
- Agent Queue System running on localhost:8000

The demo showcases:
- Submitting messages with different priorities
- Creating threaded conversations using the optional `thread_id` field
- Checking message status
- Streaming responses via Server-Sent Events (SSE)
- Cancelling queued messages
- Viewing queue summary
- Listing threads and retrieving thread metadata/messages

See the [TypeScript Client README](examples/typescript-client/README.md) for detailed documentation.

## License

[Your License Here]

## Contributing

[Contributing guidelines if applicable]

## Support

[Support information]
