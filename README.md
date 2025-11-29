# Agent Queue System

AI Agent Queue System with FastAPI and LangGraph - A production-ready message queue for processing AI agent requests with streaming support and conversation threading.

## Features

-   **Priority Queue**: Process messages based on priority (HIGH, NORMAL, LOW).
-   **Sequential Processing**: Ensures consistent agent behavior by processing one message at a time.
-   **Real-Time Streaming**: Streams agent responses chunk-by-chunk using Server-Sent Events (SSE).
-   **Conversation Threads**: Groups messages into threads for ChatGPT-like dialogues.
-   **Robust Architecture**: Built with FastAPI, Pydantic, and asyncio for high concurrency and type safety.

## Quick Start

### Prerequisites

-   Python 3.10+
-   OpenAI API Key

### Setup

1. **Clone & Install:**

    ```bash
    git clone <repository-url>
    cd agent-queue-system
    pip install -r requirements.txt
    ```

2. **Configure:**

    ```bash
    cp .env.example .env
    # Edit .env and set OPENAI_API_KEY
    ```

3. **Run:**

    ```bash
    make dev
    ```

    Or directly:

    ```bash
    uv run uvicorn shinzo.main:app --reload
    ```

The API will be available at `http://localhost:8000`.

## Documentation

-   **[Quick Start Guide](docs/QUICKSTART.md)**: Get up and running in 5 minutes.
-   **[API Reference](docs/API.md)**: Detailed endpoint documentation (Submit, Stream, Status, etc.).
-   **[Configuration](docs/CONFIGURATION.md)**: Environment variables and settings.
-   **[Development Guide](docs/DEVELOPMENT.md)**: Testing, code quality, and project structure.
-   **[Architecture](docs/ARCHITECTURE.md)**: System design, data flow, and technical decisions.
-   **[Thread Architecture](docs/THREAD_ARCHITECTURE.md)**: Deep dive into the threading model.

## Examples

-   **[TypeScript Client Demo](examples/typescript-client/)**: Complete CLI client demonstrating all features.
-   **[React Chat UI](examples/chat-ui/)**: Modern web interface for chatting with the agent.

## License

[Your License Here]
