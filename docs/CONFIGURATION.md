# Configuration

The application is configured using environment variables. You can set these in a `.env` file in the project root.

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key for LangGraph agent | - | Yes |
| `MODEL_NAME` | LLM model name to use | `gpt-4` | No |
| `MAX_QUEUE_SIZE` | Maximum number of messages allowed in queue | `1000` | No |
| `PROCESSING_TIMEOUT` | Maximum processing time per message (seconds) | `60` | No |
| `KEEPALIVE_INTERVAL` | SSE keepalive heartbeat interval (seconds) | `30` | No |
| `HOST` | Server host address | `0.0.0.0` | No |
| `PORT` | Server port | `8000` | No |
| `LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` | No |

## Example .env

```env
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-4
MAX_QUEUE_SIZE=1000
PROCESSING_TIMEOUT=60
KEEPALIVE_INTERVAL=30
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

## Setup

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API keys:
   ```bash
   nano .env
   ```

