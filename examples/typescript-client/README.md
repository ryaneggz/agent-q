# TypeScript Client Demo

A comprehensive TypeScript demonstration of the Agent Queue System API. This script showcases all API endpoints with detailed console logging.

## Prerequisites

-   **Node.js 18+** (for native fetch API support)
-   **Agent Queue System running** on `http://localhost:8000`

## Installation

```bash
npm install
```

## Running the Demo

### 1. Start the Agent Queue System API

In the project root directory:

```bash
make dev
```

Or directly:
```bash
PYTHONPATH=src uv run python -m shinzo.main
```

The API should be running on http://localhost:8000

### 2. Run the Demo

```bash
npm run demo
```

## What the Demo Does

The script demonstrates a complete workflow through 12 steps:

### 1️⃣ **Health Check**

Verifies the API server is running and healthy.

### 2️⃣ **Start Threaded Conversation**

Creates a client-side UUID and submits the first turn in a conversation thread.

### 3️⃣ **Submit Follow-up in the Same Thread**

Adds a second message with the same `thread_id` to maintain context.

### 4️⃣ **List Threads**

Calls `GET /threads` to display every active thread with summary metadata.

### 5️⃣ **Inspect Thread Metadata & Messages**

Shows how to query thread-level stats and retrieve the chronological message list.

### 6️⃣ **Submit Normal Priority Message**

Submits a standalone message (no thread) using the default priority.

### 7️⃣ **Submit High Priority Message**

Demonstrates how urgent work jumps ahead in the queue.

### 8️⃣ **Submit Low Priority Message**

Adds a background request that will be processed last.

### 9️⃣ **Check Queue Summary**

Displays the overall queue health, counts per state, and queued message previews.

### 🔟 **Check Message Status**

Queries the status endpoint for the normal-priority message, including its optional thread info.

### 1️⃣1️⃣ **Stream Message Response (SSE)**

Streams real-time events for the high-priority message, showcasing waiting/chunk/done events.

### 1️⃣2️⃣ **Cancel Queued Message & Final Summary**

Attempts to cancel the low priority job and then prints the final queue summary.

## Example Output

```
╔══════════════════════════════════════════════════════════╗
║   Agent Queue System - TypeScript Client Demo           ║
╚══════════════════════════════════════════════════════════╝

1️⃣  Checking server health
────────────────────────────────────────────────────────────
[HEALTH] Checking server health...
✓ Server is healthy

2️⃣  Submitting normal priority message
────────────────────────────────────────────────────────────
[SUBMIT] Sending message...
  Message: "What is the capital of France?"
  Priority: normal
[RESPONSE]
{
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "queued",
  "queue_position": 0,
  "created_at": "2024-01-15T10:30:00.000Z"
}

...

7️⃣  Streaming message response
────────────────────────────────────────────────────────────
Note: This will stream real-time events from the agent
[STREAM] Starting SSE stream for 650e8400...
[SSE EVENT] waiting
[SSE DATA] { state: 'queued', position: 0, message: 'Waiting in queue' }
[SSE EVENT] chunk
[SSE DATA] { type: 'content', chunk: 'The answer is 4.', index: 0 }
[SSE EVENT] done
[SSE DATA] { state: 'completed', result: 'The answer is 4.', completed_at: '...' }
[STREAM] Connection closed

✅ Demo completed successfully!
```

## API Endpoints Demonstrated

| Endpoint                        | Method | Purpose                                          |
| ------------------------------- | ------ | ------------------------------------------------ |
| `/health`                       | GET    | Health check                                     |
| `/messages`                     | POST   | Submit message (with optional `thread_id`)       |
| `/messages/{id}/status`         | GET    | Check message status                             |
| `/messages/{id}/stream`         | GET    | Stream SSE events                                |
| `/messages/{id}`                | DELETE | Cancel message                                   |
| `/queue`                        | GET    | Get queue summary                                |
| `/threads`                      | GET    | List threads with summary metadata               |
| `/threads/{thread_id}`          | GET    | Retrieve thread metadata (counts, last activity) |
| `/threads/{thread_id}/messages` | GET    | Fetch chronological messages within a thread     |

## Files

-   **`client-demo.ts`** - Main demo script with all API functions
-   **`types.ts`** - TypeScript interfaces matching the API models
-   **`package.json`** - Dependencies and scripts
-   **`tsconfig.json`** - TypeScript configuration

## Type Safety

All API responses are fully typed with TypeScript interfaces that match the Pydantic models from the FastAPI backend:

```typescript
interface MessageSubmitResponse {
    message_id: string;
    state: MessageState;
    queue_position: number | null;
    created_at: string;
}

enum MessageState {
    QUEUED = "queued",
    PROCESSING = "processing",
    COMPLETED = "completed",
    FAILED = "failed",
    CANCELLED = "cancelled",
}
```

## Troubleshooting

### "Failed to connect to API"

-   Make sure the Agent Queue System is running: `make dev`
-   Check that it's listening on http://localhost:8000
-   Verify no firewall is blocking the connection

### "Message not found" errors

-   The demo may run faster than the agent can process messages
-   This is normal and demonstrates error handling
-   The agent needs an OpenAI API key to actually process messages

### SSE stream doesn't show chunks

-   The agent needs to be configured with a valid OpenAI API key
-   Check `.env` file in the project root has `OPENAI_API_KEY` set
-   Without a valid key, messages will fail rather than complete

### Type errors when building

-   Run `npm run type-check` to see TypeScript errors
-   Ensure TypeScript version is 5.3.0 or higher
-   Check that `@types/node` is installed

## Environment Variables

You can customize the API URL:

```bash
API_BASE_URL=http://localhost:8080 npm run demo
```

## Development

### Type checking only (no execution)

```bash
npm run type-check
```

### Build to JavaScript

```bash
npm run build
```

Output will be in the `dist/` directory.

## Using as a Starting Point

This demo script can serve as a starting point for building your own client:

1. **Copy the type definitions** from `types.ts`
2. **Adapt the API functions** from `client-demo.ts`
3. **Add error handling** appropriate for your use case
4. **Add retry logic** if needed for production use

## Notes

-   The demo uses native `fetch` API (Node.js 18+)
-   No external HTTP libraries required
-   Console output uses ANSI color codes for readability
-   SSE streaming is implemented with manual parsing (educational)
-   Error handling is basic for demonstration purposes

## License

Same as the main project.
