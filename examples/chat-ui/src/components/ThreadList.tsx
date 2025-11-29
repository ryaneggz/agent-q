import type { ThreadSummary } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageSquare, Plus } from "lucide-react";

interface ThreadListProps {
  threads: ThreadSummary[];
  currentThreadId: string | null;
  onSelectThread: (threadId: string) => void;
  onNewThread: () => void;
}

export function ThreadList({
  threads,
  currentThreadId,
  onSelectThread,
  onNewThread,
}: ThreadListProps) {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Threads
          </CardTitle>
          <Button onClick={onNewThread} size="sm" variant="outline">
            <Plus className="h-4 w-4 mr-1" />
            New
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden p-0">
        <ScrollArea className="h-full">
          {threads.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              No threads yet. Start a new conversation!
            </div>
          ) : (
            <div className="space-y-2 p-4 pt-0">
              {threads.map((thread) => (
                <Card
                  key={thread.thread_id}
                  className={`cursor-pointer transition-colors hover:bg-accent ${
                    currentThreadId === thread.thread_id
                      ? "border-primary bg-accent"
                      : ""
                  }`}
                  onClick={() => onSelectThread(thread.thread_id)}
                >
                  <CardContent className="p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          {thread.last_message_preview || "Empty thread"}
                        </p>
                        <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                          <Badge variant="secondary" className="text-xs">
                            {thread.message_count} messages
                          </Badge>
                          <span>{formatDate(thread.last_activity)}</span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
