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
}

export interface MessageSubmitResponse {
  message_id: string;
  state: MessageState;
  queue_position: number | null;
  created_at: string;
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

export interface SSEEvent {
  event?: string;
  data: any;
}

export interface HealthResponse {
  status: string;
  queue_initialized: boolean;
}
