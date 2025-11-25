# TypeScript Client Demo

A comprehensive TypeScript demonstration of the Agent Queue System API. This script showcases all API endpoints with detailed console logging.

## Prerequisites

- **Node.js 18+** (for native fetch API support)
- **Agent Queue System running** on `http://localhost:8000`

## Installation

```bash
npm install
```

## Running the Demo

### 1. Start the Agent Queue System API

In the project root directory:

```bash
uv run python -m app.main
```

The API should be running on http://localhost:8000

### 2. Run the Demo

```bash
npm run demo
```

## What the Demo Does

The script demonstrates a complete workflow through 9 steps:

### 1️⃣ **Health Check**
Verifies the API server is running and healthy

### 2️⃣ **Submit Normal Priority Message**
Submits a message with normal priority to the queue
```typescript
"What is the capital of France?" - Priority: NORMAL
```

### 3️⃣ **Submit High Priority Message**
Submits an urgent message that jumps ahead in the queue
```typescript
"Urgent: Calculate 2+2" - Priority: HIGH
```

### 4️⃣ **Submit Low Priority Message**
Submits a low priority message that processes last
```typescript
"Tell me a joke" - Priority: LOW
```

### 5️⃣ **Check Queue Summary**
Displays the current state of the queue showing:
- Total messages in each state (queued, processing, completed, failed, cancelled)
- List of queued messages with priorities
- Currently processing message

### 6️⃣ **Check Message Status**
Queries the status of a specific message showing:
- Current state
- Queue position (if queued)
- Result (if completed)
- Timestamps

### 7️⃣ **Stream Message Response (SSE)**
Demonstrates real-time streaming of agent responses using Server-Sent Events:
- Waiting events while message is queued
- Content chunks as the agent generates them
- Completion/error/cancellation events

### 8️⃣ **Cancel Queued Message**
Attempts to cancel the low priority message before it processes

### 9️⃣ **Final Queue Summary**
Shows the final state of the queue after all operations

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

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/messages` | POST | Submit message |
| `/messages/{id}/status` | GET | Check message status |
| `/messages/{id}/stream` | GET | Stream SSE events |
| `/messages/{id}` | DELETE | Cancel message |
| `/queue` | GET | Get queue summary |

## Files

- **`client-demo.ts`** - Main demo script with all API functions
- **`types.ts`** - TypeScript interfaces matching the API models
- **`package.json`** - Dependencies and scripts
- **`tsconfig.json`** - TypeScript configuration

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
- Make sure the Agent Queue System is running: `uv run python -m app.main`
- Check that it's listening on http://localhost:8000
- Verify no firewall is blocking the connection

### "Message not found" errors
- The demo may run faster than the agent can process messages
- This is normal and demonstrates error handling
- The agent needs an OpenAI API key to actually process messages

### SSE stream doesn't show chunks
- The agent needs to be configured with a valid OpenAI API key
- Check `.env` file in the project root has `OPENAI_API_KEY` set
- Without a valid key, messages will fail rather than complete

### Type errors when building
- Run `npm run type-check` to see TypeScript errors
- Ensure TypeScript version is 5.3.0 or higher
- Check that `@types/node` is installed

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

- The demo uses native `fetch` API (Node.js 18+)
- No external HTTP libraries required
- Console output uses ANSI color codes for readability
- SSE streaming is implemented with manual parsing (educational)
- Error handling is basic for demonstration purposes

## License

Same as the main project.
