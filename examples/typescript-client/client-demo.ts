#!/usr/bin/env node
/**
 * Agent Queue System - TypeScript Client Demo
 *
 * This script demonstrates all API endpoints with clear console logging.
 * Run: npm run demo
 */

import {
  MessageState,
  Priority,
  MessageSubmitResponse,
  MessageStatusResponse,
  QueueSummaryResponse,
  HealthResponse,
} from "./types.js";

// Configuration
const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:8000";

// ANSI color codes for console output
const COLORS = {
  reset: "\x1b[0m",
  bright: "\x1b[1m",
  dim: "\x1b[2m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
  magenta: "\x1b[35m",
  cyan: "\x1b[36m",
  red: "\x1b[31m",
};

/**
 * Utility function to sleep for a given duration
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Pretty print JSON with colors
 */
function logJSON(data: any): void {
  console.log(JSON.stringify(data, null, 2));
}

/**
 * Check if the API server is healthy
 */
async function checkHealth(): Promise<HealthResponse> {
  console.log(`${COLORS.cyan}[HEALTH]${COLORS.reset} Checking server health...`);

  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    const data = (await response.json()) as HealthResponse;

    if (data.status === "healthy") {
      console.log(`${COLORS.green}✓ Server is healthy${COLORS.reset}`);
    } else {
      console.log(`${COLORS.yellow}⚠ Server status: ${data.status}${COLORS.reset}`);
    }

    return data;
  } catch (error) {
    console.error(
      `${COLORS.red}✗ Failed to connect to API at ${API_BASE_URL}${COLORS.reset}`
    );
    console.error(`${COLORS.dim}  Make sure the Agent Queue System is running${COLORS.reset}`);
    console.error(`${COLORS.dim}  Start it with: uv run python -m app.main${COLORS.reset}`);
    throw error;
  }
}

/**
 * Submit a message to the queue
 */
async function submitMessage(
  message: string,
  priority: Priority = Priority.NORMAL
): Promise<MessageSubmitResponse> {
  console.log(`${COLORS.cyan}[SUBMIT]${COLORS.reset} Sending message...`);
  console.log(`${COLORS.dim}  Message: "${message}"${COLORS.reset}`);
  console.log(`${COLORS.dim}  Priority: ${priority}${COLORS.reset}`);

  const response = await fetch(`${API_BASE_URL}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, priority }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const data = (await response.json()) as MessageSubmitResponse;
  console.log(`${COLORS.green}[RESPONSE]${COLORS.reset}`);
  logJSON(data);

  return data;
}

/**
 * Get the status of a message
 */
async function getMessageStatus(
  messageId: string
): Promise<MessageStatusResponse> {
  console.log(
    `${COLORS.cyan}[STATUS]${COLORS.reset} Checking message ${messageId.substring(0, 8)}...`
  );

  const response = await fetch(`${API_BASE_URL}/messages/${messageId}/status`);

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Message not found: ${messageId}`);
    }
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const data = (await response.json()) as MessageStatusResponse;
  console.log(`${COLORS.green}[RESPONSE]${COLORS.reset} State: ${data.state}`);
  if (data.queue_position !== null) {
    console.log(`${COLORS.dim}  Queue position: ${data.queue_position}${COLORS.reset}`);
  }
  if (data.result) {
    console.log(`${COLORS.dim}  Result: ${data.result.substring(0, 100)}...${COLORS.reset}`);
  }

  return data;
}

/**
 * Stream message processing events via SSE
 */
async function streamMessage(messageId: string): Promise<void> {
  console.log(
    `${COLORS.cyan}[STREAM]${COLORS.reset} Starting SSE stream for ${messageId.substring(0, 8)}...`
  );

  const response = await fetch(`${API_BASE_URL}/messages/${messageId}/stream`);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("No reader available for response body");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        console.log(`${COLORS.dim}[STREAM] Connection closed${COLORS.reset}`);
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data:")) {
          const dataStr = line.substring(5).trim();
          if (dataStr) {
            try {
              const data = JSON.parse(dataStr) as any;
              console.log(`${COLORS.magenta}[SSE DATA]${COLORS.reset}`, data);

              // Exit stream on terminal events
              if (
                data.state === "completed" ||
                data.state === "failed" ||
                data.state === "cancelled"
              ) {
                reader.cancel();
                return;
              }
            } catch (e) {
              console.log(`${COLORS.dim}[SSE] ${dataStr}${COLORS.reset}`);
            }
          }
        } else if (line.startsWith("event:")) {
          const eventType = line.substring(6).trim();
          console.log(`${COLORS.yellow}[SSE EVENT]${COLORS.reset} ${eventType}`);
        } else if (line.startsWith(":")) {
          // Keepalive comment
          console.log(`${COLORS.dim}[SSE] keepalive${COLORS.reset}`);
        }
      }
    }
  } catch (error) {
    console.error(`${COLORS.red}[STREAM ERROR]${COLORS.reset}`, error);
  } finally {
    reader.releaseLock();
  }
}

/**
 * Cancel a queued message
 */
async function cancelMessage(messageId: string): Promise<void> {
  console.log(
    `${COLORS.cyan}[CANCEL]${COLORS.reset} Cancelling message ${messageId.substring(0, 8)}...`
  );

  const response = await fetch(`${API_BASE_URL}/messages/${messageId}`, {
    method: "DELETE",
  });

  if (response.status === 409) {
    console.log(
      `${COLORS.yellow}[CONFLICT]${COLORS.reset} Cannot cancel - message is already processing`
    );
    return;
  }

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const data = (await response.json()) as { message: string };
  console.log(`${COLORS.green}[RESPONSE]${COLORS.reset}`, data.message);
}

/**
 * Get queue summary
 */
async function getQueueSummary(): Promise<QueueSummaryResponse> {
  console.log(`${COLORS.cyan}[QUEUE]${COLORS.reset} Fetching queue summary...`);

  const response = await fetch(`${API_BASE_URL}/queue`);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const data = (await response.json()) as QueueSummaryResponse;

  console.log(`${COLORS.green}[SUMMARY]${COLORS.reset}`);
  console.log(`  Queued: ${data.total_queued}`);
  console.log(`  Processing: ${data.total_processing}`);
  console.log(`  Completed: ${data.total_completed}`);
  console.log(`  Failed: ${data.total_failed}`);
  console.log(`  Cancelled: ${data.total_cancelled}`);

  if (data.queued_messages.length > 0) {
    console.log(`${COLORS.dim}  Queued messages:${COLORS.reset}`);
    data.queued_messages.forEach((msg, idx) => {
      console.log(
        `${COLORS.dim}    ${idx + 1}. [${msg.priority}] ${msg.user_message.substring(0, 50)}...${COLORS.reset}`
      );
    });
  }

  if (data.current_processing) {
    console.log(`${COLORS.dim}  Currently processing:${COLORS.reset}`);
    console.log(
      `${COLORS.dim}    [${data.current_processing.priority}] ${data.current_processing.user_message.substring(0, 50)}...${COLORS.reset}`
    );
  }

  return data;
}

/**
 * Main demo workflow
 */
async function main() {
  console.log(
    `${COLORS.bright}${COLORS.blue}╔══════════════════════════════════════════════════════════╗${COLORS.reset}`
  );
  console.log(
    `${COLORS.bright}${COLORS.blue}║   Agent Queue System - TypeScript Client Demo           ║${COLORS.reset}`
  );
  console.log(
    `${COLORS.bright}${COLORS.blue}╚══════════════════════════════════════════════════════════╝${COLORS.reset}\n`
  );

  try {
    // Step 1: Health check
    console.log(`${COLORS.bright}1️⃣  Checking server health${COLORS.reset}`);
    console.log("─".repeat(60));
    await checkHealth();
    await sleep(1000);

    // Step 2: Submit normal priority message
    console.log(`\n${COLORS.bright}2️⃣  Submitting normal priority message${COLORS.reset}`);
    console.log("─".repeat(60));
    const msg1 = await submitMessage(
      "What is the capital of France?",
      Priority.NORMAL
    );
    await sleep(500);

    // Step 3: Submit high priority message
    console.log(`\n${COLORS.bright}3️⃣  Submitting high priority message${COLORS.reset}`);
    console.log("─".repeat(60));
    const msg2 = await submitMessage(
      "Urgent: Calculate 2+2",
      Priority.HIGH
    );
    await sleep(500);

    // Step 4: Submit low priority message
    console.log(`\n${COLORS.bright}4️⃣  Submitting low priority message${COLORS.reset}`);
    console.log("─".repeat(60));
    const msg3 = await submitMessage("Tell me a joke", Priority.LOW);
    await sleep(500);

    // Step 5: Check queue summary
    console.log(`\n${COLORS.bright}5️⃣  Checking queue summary${COLORS.reset}`);
    console.log("─".repeat(60));
    await getQueueSummary();
    await sleep(1000);

    // Step 6: Check message status
    console.log(`\n${COLORS.bright}6️⃣  Checking message status${COLORS.reset}`);
    console.log("─".repeat(60));
    await getMessageStatus(msg1.message_id);
    await sleep(500);

    // Step 7: Stream a message response
    console.log(`\n${COLORS.bright}7️⃣  Streaming message response${COLORS.reset}`);
    console.log("─".repeat(60));
    console.log(`${COLORS.dim}Note: This will stream real-time events from the agent${COLORS.reset}`);
    await streamMessage(msg2.message_id);
    await sleep(1000);

    // Step 8: Cancel a queued message
    console.log(`\n${COLORS.bright}8️⃣  Cancelling queued message${COLORS.reset}`);
    console.log("─".repeat(60));
    await cancelMessage(msg3.message_id);
    await sleep(500);

    // Step 9: Final queue summary
    console.log(`\n${COLORS.bright}9️⃣  Final queue summary${COLORS.reset}`);
    console.log("─".repeat(60));
    await getQueueSummary();

    console.log(`\n${COLORS.green}${COLORS.bright}✅ Demo completed successfully!${COLORS.reset}\n`);
  } catch (error) {
    console.error(
      `\n${COLORS.red}${COLORS.bright}❌ Demo failed${COLORS.reset}`
    );
    console.error(error);
    process.exit(1);
  }
}

// Run the demo
main();
