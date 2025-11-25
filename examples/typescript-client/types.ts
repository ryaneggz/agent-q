/**
 * Type definitions for Agent Queue System API
 * Matches the Pydantic models from the Python backend
 */

export enum MessageState {
  QUEUED = "queued",
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed",
  CANCELLED = "cancelled",
}

export enum Priority {
  HIGH = "high",
  NORMAL = "normal",
  LOW = "low",
}

export interface MessageSubmitRequest {
  message: string;
  priority: Priority;
  thread_id?: string | null;
}

export interface MessageSubmitResponse {
  message_id: string;
  state: MessageState;
  queue_position: number | null;
  created_at: string;
  thread_id: string | null;
}

export interface MessageStatusResponse {
  message_id: string;
  state: MessageState;
  user_message: string;
  priority: Priority;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  result: string | null;
  error: string | null;
  queue_position: number | null;
  thread_id: string | null;
}

export interface QueueSummaryResponse {
  total_queued: number;
  total_processing: number;
  total_completed: number;
  total_failed: number;
  total_cancelled: number;
  queued_messages: Array<{
    id: string;
    priority: string;
    created_at: string;
    user_message: string;
  }>;
  current_processing: {
    id: string;
    priority: string;
    started_at: string;
    user_message: string;
  } | null;
}

export interface ThreadMetadata {
  thread_id: string;
  message_count: number;
  created_at: string;
  last_activity: string;
  states: Record<string, number>;
}

export interface ThreadSummary {
  thread_id: string;
  message_count: number;
  created_at: string;
  last_activity: string;
  last_message_preview: string | null;
}

export interface ThreadMessagesResponse {
  thread_id: string;
  total_messages: number;
  messages: MessageStatusResponse[];
}

export interface SSEEvent {
  event?: string;
  data: any;
}

export interface HealthResponse {
  status: string;
  queue_initialized: boolean;
}
