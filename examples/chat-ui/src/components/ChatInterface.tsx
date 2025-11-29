import { useState, useEffect, useRef } from "react";
import type { MessageStatusResponse, ThreadSummary } from "@/types/api";
import { Priority, MessageState } from "@/types/api";
import { apiClient } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatMessage } from "./ChatMessage";
import { ThreadList } from "./ThreadList";
import { Send, RefreshCw } from "lucide-react";

export function ChatInterface() {
    const [threads, setThreads] = useState<ThreadSummary[]>([]);
    const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
    const [messages, setMessages] = useState<MessageStatusResponse[]>([]);
    const [inputValue, setInputValue] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [streamingContent, setStreamingContent] = useState<
        Record<string, string>
    >({});
    const scrollRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    // Load threads on mount
    useEffect(() => {
        loadThreads();
    }, []);

    // Load messages when thread changes
    useEffect(() => {
        if (currentThreadId) {
            loadThreadMessages(currentThreadId);
        } else {
            setMessages([]);
        }
    }, [currentThreadId]);

    // Auto-scroll to bottom when messages change
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, streamingContent]);

    // Auto-focus input on mount and when starting new thread
    useEffect(() => {
        inputRef.current?.focus();
    }, [currentThreadId]);

    const loadThreads = async () => {
        try {
            const threadList = await apiClient.listThreads();
            setThreads(threadList);
        } catch (error) {
            console.error("Failed to load threads:", error);
        }
    };

    const loadThreadMessages = async (threadId: string) => {
        try {
            const response = await apiClient.getThreadMessages(threadId);
            setMessages(response.messages);

            // Start streaming for any processing messages
            response.messages.forEach((msg) => {
                if (msg.state === MessageState.PROCESSING) {
                    startStreaming(msg.message_id);
                }
            });
        } catch (error) {
            console.error("Failed to load thread messages:", error);
        }
    };

    const startStreaming = async (messageId: string) => {
        await apiClient.streamMessage(
            messageId,
            (event, data) => {
                if (event === "chunk") {
                    setStreamingContent((prev) => ({
                        ...prev,
                        [messageId]: (prev[messageId] || "") + data.chunk,
                    }));
                } else if (event === "done") {
                    // Refresh the message to get final result
                    refreshMessage(messageId);
                    setStreamingContent((prev) => {
                        const newState = { ...prev };
                        delete newState[messageId];
                        return newState;
                    });
                }
            },
            (error) => {
                console.error("Streaming error:", error);
            }
        );
    };

    const refreshMessage = async (messageId: string) => {
        try {
            const updatedMessage = await apiClient.getMessageStatus(messageId);
            setMessages((prev) =>
                prev.map((msg) =>
                    msg.message_id === messageId ? updatedMessage : msg
                )
            );
        } catch (error) {
            console.error("Failed to refresh message:", error);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!inputValue.trim() || isLoading) return;

        setIsLoading(true);
        const messageText = inputValue;
        setInputValue("");

        try {
            const isNewThread = !currentThreadId;

            // Submit message - thread_id is optional and will be generated on backend if not provided
            const response = await apiClient.submitMessage({
                message: messageText,
                priority: Priority.NORMAL,
                thread_id: currentThreadId,
            });

            // If new thread, set the thread_id returned by the backend
            if (isNewThread && response.thread_id) {
                setCurrentThreadId(response.thread_id);
                await loadThreads();
            }

            // Reload messages to show the newly submitted message
            const threadId = response.thread_id || currentThreadId;
            if (threadId) {
                await loadThreadMessages(threadId);
            }

            // Start streaming the response immediately
            startStreaming(response.message_id);
        } catch (error) {
            console.error("Failed to submit message:", error);
        } finally {
            setIsLoading(false);
            // Refocus input after submission - use setTimeout to ensure DOM has updated
            setTimeout(() => {
                inputRef.current?.focus();
            }, 0);
        }
    };

    const handleNewThread = () => {
        setCurrentThreadId(null);
        setMessages([]);
        setStreamingContent({});
    };

    const handleSelectThread = (threadId: string) => {
        setCurrentThreadId(threadId);
        setStreamingContent({});
    };

    return (
        <div className="h-screen flex gap-4 p-4 bg-background">
            {/* Threads Sidebar */}
            <div className="w-80 flex-shrink-0">
                <ThreadList
                    threads={threads}
                    currentThreadId={currentThreadId}
                    onSelectThread={handleSelectThread}
                    onNewThread={handleNewThread}
                />
            </div>

            {/* Chat Area */}
            <Card className="flex-1 flex flex-col">
                <CardHeader className="border-b">
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-lg">
                            {currentThreadId
                                ? `Thread: ${currentThreadId.slice(0, 20)}...`
                                : "New Conversation"}
                        </CardTitle>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() =>
                                currentThreadId &&
                                loadThreadMessages(currentThreadId)
                            }
                        >
                            <RefreshCw className="h-4 w-4" />
                        </Button>
                    </div>
                </CardHeader>

                <CardContent className="flex-1 flex flex-col p-0 overflow-hidden">
                    {/* Messages */}
                    <ScrollArea ref={scrollRef} className="flex-1 p-4">
                        {messages.length === 0 ? (
                            <div className="h-full flex items-center justify-center text-center text-muted-foreground">
                                <div>
                                    <p className="text-lg font-medium">
                                        No messages yet
                                    </p>
                                    <p className="text-sm mt-1">
                                        Start a conversation below
                                    </p>
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {messages.map((message) => (
                                    <ChatMessage
                                        key={message.message_id}
                                        message={message}
                                        streamingContent={
                                            streamingContent[message.message_id]
                                        }
                                    />
                                ))}
                            </div>
                        )}
                    </ScrollArea>

                    {/* Input Area */}
                    <div className="border-t p-4">
                        <form onSubmit={handleSubmit} className="flex gap-2">
                            <Input
                                ref={inputRef}
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                placeholder="Type your message..."
                                disabled={isLoading}
                                className="flex-1"
                            />
                            <Button
                                type="submit"
                                disabled={isLoading || !inputValue.trim()}
                            >
                                <Send className="h-4 w-4" />
                            </Button>
                        </form>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
