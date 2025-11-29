import type { MessageStatusResponse } from "@/types/api";
import { MessageState } from "@/types/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";
import { MarkdownRenderer } from "./MarkdownRenderer";

interface ChatMessageProps {
  message: MessageStatusResponse;
  streamingContent?: string;
}

const getStateIcon = (state: MessageState) => {
  switch (state) {
    case MessageState.QUEUED:
      return <Clock className="h-4 w-4" />;
    case MessageState.PROCESSING:
      return <Loader2 className="h-4 w-4 animate-spin" />;
    case MessageState.COMPLETED:
      return <CheckCircle2 className="h-4 w-4" />;
    case MessageState.FAILED:
    case MessageState.CANCELLED:
      return <XCircle className="h-4 w-4" />;
  }
};

const getStateColor = (state: MessageState): "default" | "secondary" | "destructive" | "outline" => {
  switch (state) {
    case MessageState.QUEUED:
      return "secondary";
    case MessageState.PROCESSING:
    case MessageState.COMPLETED:
      return "default";
    case MessageState.FAILED:
    case MessageState.CANCELLED:
      return "destructive";
    default:
      return "default";
  }
};

export function ChatMessage({ message, streamingContent }: ChatMessageProps) {
  const isStreaming = message.state === MessageState.PROCESSING && streamingContent;

  return (
    <div className="space-y-2">
      {/* User Message */}
      <Card className="ml-auto max-w-[80%] bg-primary text-primary-foreground">
        <CardContent className="p-3">
          <p className="text-sm">{message.user_message}</p>
          <div className="mt-2 flex items-center gap-2 text-xs opacity-80">
            <Badge variant="outline" className="border-primary-foreground/20">
              {message.priority}
            </Badge>
            {message.queue_position !== null && (
              <span>Queue: #{message.queue_position}</span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Agent Response */}
      {(message.result || isStreaming || message.error) && (
        <Card className={cn("mr-auto max-w-[80%]")}>
          <CardContent className="p-3">
            <div className="flex items-start gap-2">
              <div className="mt-0.5">{getStateIcon(message.state)}</div>
              <div className="flex-1 space-y-2 min-w-0">
                <div className="flex items-center gap-2">
                  <Badge variant={getStateColor(message.state)} className="text-xs">
                    {message.state}
                  </Badge>
                </div>

                {message.error && (
                  <p className="text-sm text-destructive">{message.error}</p>
                )}

                {isStreaming && (
                  <MarkdownRenderer content={streamingContent} />
                )}

                {message.result && !isStreaming && (
                  <MarkdownRenderer content={message.result} />
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
