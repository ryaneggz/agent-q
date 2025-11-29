# Chat UI - Agent Queue System

A React-based chat interface with thread support for the Agent Queue System. This UI demonstrates the message threading capabilities of the Agent Queue System in a user-friendly chat format.

## Features

- **Thread Management**: Create and switch between multiple conversation threads
- **Real-time Streaming**: See agent responses stream in real-time via Server-Sent Events (SSE)
- **Thread List**: Browse all your conversation threads with message counts and previews
- **Message States**: Visual indicators for message states (queued, processing, completed, failed)
- **Priority Support**: Messages support priority levels (high, normal, low)
- **Responsive Design**: Built with Tailwind CSS and shadcn/ui components

## Prerequisites

- Node.js 18+ (for native fetch API)
- Agent Queue System API running on `http://localhost:8000`

## Installation

```bash
cd examples/chat-ui
npm install
```

## Running the Chat UI

1. Make sure the Agent Queue System API is running:
```bash
# From the project root
uv run python -m app.main
```

2. Start the dev server:
```bash
npm run dev
```

3. Open your browser to `http://localhost:5173`

## Usage

### Starting a New Thread

1. Click the **"New"** button in the threads panel
2. Type your message in the input box
3. Click Send or press Enter
4. A new thread will be created automatically

### Switching Between Threads

1. Click on any thread in the left sidebar
2. The chat area will load all messages from that thread
3. Continue the conversation by typing new messages

### Understanding Message States

- **Queued** (Clock icon): Message is waiting to be processed
- **Processing** (Spinning icon): Agent is currently working on the message
- **Completed** (Checkmark): Agent has finished processing
- **Failed** (X icon): Processing failed with an error
- **Cancelled** (X icon): Message was cancelled

## Architecture

The chat UI follows a component-based architecture:

```
ChatInterface (Main Component)
├── ThreadList (Sidebar)
│   └── Thread Cards
└── Chat Area
    ├── Message List
    │   └── ChatMessage (Individual messages)
    └── Input Form
```

### Key Components

- **ChatInterface**: Main component managing state and API calls
- **ThreadList**: Displays all threads with metadata
- **ChatMessage**: Renders individual messages with state indicators
- **API Client**: Handles all communication with the backend

### State Management

The UI uses React hooks for state management:
- `threads`: List of all conversation threads
- `currentThreadId`: Currently selected thread
- `messages`: Messages in the current thread
- `streamingContent`: Real-time streaming chunks

## API Integration

The UI integrates with these API endpoints:

- `POST /messages` - Submit new messages with thread_id
- `GET /messages/{id}/status` - Get message status
- `GET /messages/{id}/stream` - Stream agent responses (SSE)
- `GET /threads` - List all threads
- `GET /threads/{id}/messages` - Get messages for a thread

## Technology Stack

- **React 18**: UI framework
- **TypeScript**: Type safety
- **Vite**: Build tool and dev server
- **Tailwind CSS**: Utility-first styling
- **shadcn/ui**: Component library
- **Lucide React**: Icon library

## Development

### Build for Production

```bash
npm run build
```

The build output will be in the `dist/` directory.

### Type Checking

```bash
npm run type-check
```

## Troubleshooting

### API Connection Issues

If you see connection errors:
1. Verify the Agent Queue System is running on port 8000
2. Check the `API_BASE_URL` in `src/lib/api.ts`
3. Ensure no CORS issues (API should allow localhost:5173)

### Streaming Not Working

If messages don't stream in real-time:
1. Check browser console for SSE connection errors
2. Verify the `/messages/{id}/stream` endpoint is accessible
3. Ensure the agent is properly initialized in the backend

### Thread Not Loading

If thread messages don't load:
1. Check that the thread_id exists in the backend
2. Verify the GET /threads/{id}/messages endpoint is working
3. Look for 404 errors in the browser console

## Future Enhancements

- Message editing and deletion
- Thread naming and descriptions
- Search within threads
- Export thread history
- Dark mode toggle
- User authentication
- Thread sharing
- Markdown rendering for agent responses
