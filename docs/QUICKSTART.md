# Quick Start Guide

Get the Agent Queue System up and running in 5 minutes.

## Prerequisites

- Python 3.10 or higher
- OpenAI API key

## Installation

1. **Install uv** (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. **Install dependencies**:
```bash
uv sync
```

3. **Configure environment**:
```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:
```env
OPENAI_API_KEY=sk-your-key-here
```

## Run the Server

```bash
make dev
```

Or directly:
```bash
PYTHONPATH=src uv run python -m shinzo.main
```

The server will start on http://localhost:8000

## Test It Out

### 1. Submit a Message

```bash
curl -X POST http://localhost:8000/messages \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the capital of France?", "priority": "normal"}'
```

Response:
```json
{
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "queued",
  "queue_position": 0,
  "created_at": "2024-01-15T10:30:00.000Z"
}
```

### 2. Stream the Response

```bash
curl -N http://localhost:8000/messages/{message_id}/stream
```

You'll see real-time events:
```
event: waiting
data: {"state": "queued", "position": 0, "message": "Waiting in queue"}

event: chunk
data: {"type": "content", "chunk": "The capital of France is Paris.", "index": 0}

event: done
data: {"state": "completed", "result": "The capital of France is Paris.", "completed_at": "..."}
```

### 3. Check Status

```bash
curl http://localhost:8000/messages/{message_id}/status
```

### 4. View Queue

```bash
curl http://localhost:8000/queue
```

## Using Docker

```bash
# Build and run
docker-compose up

# Test
curl http://localhost:8000/health
```

## Next Steps

- Read the full [README.md](../README.md) for detailed documentation
- Explore the [API Reference](API.md) for endpoint details
- Check out the [Architecture Guide](ARCHITECTURE.md) for system design
- See the [Development Guide](DEVELOPMENT.md) for contributing

## Troubleshooting

**Can't connect to server?**
- Check that port 8000 is not already in use
- Verify Python 3.10+ is installed: `python --version`

**API key error?**
- Ensure your OpenAI API key is valid and has credits
- Check the `.env` file is in the project root

**Import errors?**
- Run `uv sync` to ensure all dependencies are installed
- Use `uv run` prefix for all Python commands
