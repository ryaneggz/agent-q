import type { MessageStatusResponse } from "@/types/api";
import { MessageState } from "@/types/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";

interface ChatMessageProps {
  message: MessageStatusResponse;
  streamingContent?: string;
}

export function ChatMessage({ message, streamingContent }: ChatMessageProps) {
  const isStreaming = message.state === MessageState.PROCESSING && streamingContent;

  const getStateIcon = () => {
    switch (message.state) {
      case MessageState.QUEUED:
        return <Clock className="h-4 w-4" />;
      case MessageState.PROCESSING:
        return <Loader2 className="h-4 w-4 animate-spin" />;
      case MessageState.COMPLETED:
        return <CheckCircle2 className="h-4 w-4" />;
      case MessageState.FAILED:
        return <XCircle className="h-4 w-4" />;
      case MessageState.CANCELLED:
        return <XCircle className="h-4 w-4" />;
    }
  };

  const getStateColor = () => {
    switch (message.state) {
      case MessageState.QUEUED:
        return "secondary";
      case MessageState.PROCESSING:
        return "default";
      case MessageState.COMPLETED:
        return "default";
      case MessageState.FAILED:
        return "destructive";
      case MessageState.CANCELLED:
        return "destructive";
    }
  };

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
              <div className="mt-0.5">{getStateIcon()}</div>
              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-2">
                  <Badge variant={getStateColor()} className="text-xs">
                    {message.state}
                  </Badge>
                </div>

                {message.error && (
                  <p className="text-sm text-destructive">{message.error}</p>
                )}

                {isStreaming && (
                  <p className="text-sm whitespace-pre-wrap">{streamingContent}</p>
                )}

                {message.result && !isStreaming && (
                  <p className="text-sm whitespace-pre-wrap">{message.result}</p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
