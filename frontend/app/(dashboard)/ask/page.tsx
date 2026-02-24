"use client";

import { useState, useRef, useEffect } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  useAskQuestion,
  useConversations,
  useConversation,
  useDeleteConversation,
  useSuggestedQuestions,
} from "@/hooks/queries/useAI";
import { ChatSidebar } from "@/components/ai/ChatSidebar";
import { ChatInput } from "@/components/ai/ChatInput";
import { AIMessage } from "@/components/ai/AIMessage";
import { SuggestedQuestions } from "@/components/ai/SuggestedQuestions";
import { ThinkingIndicator } from "@/components/ai/ThinkingIndicator";
import type { AIMessage as AIMessageType } from "@/types/ai";

export default function AskPage() {
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null);
  const [localMessages, setLocalMessages] = useState<AIMessageType[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Queries
  const { data: conversations = [], isLoading: conversationsLoading } = useConversations();
  const { data: conversationDetail } = useConversation(currentConversationId);
  const { data: suggestions = [], isLoading: suggestionsLoading } = useSuggestedQuestions();

  // Mutations
  const askMutation = useAskQuestion();
  const deleteMutation = useDeleteConversation();

  // Sync messages from conversation detail
  useEffect(() => {
    if (conversationDetail?.messages) {
      setLocalMessages(conversationDetail.messages);
    }
  }, [conversationDetail]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [localMessages, askMutation.isPending]);

  const handleSendMessage = async (question: string) => {
    // Optimistically add user message
    const userMessage: AIMessageType = {
      id: Date.now(),
      role: "user",
      content: question,
      created_at: new Date().toISOString(),
    };
    setLocalMessages((prev) => [...prev, userMessage]);

    try {
      const response = await askMutation.mutateAsync({
        question,
        conversation_id: currentConversationId || undefined,
      });

      // Update conversation ID if new
      if (!currentConversationId) {
        setCurrentConversationId(response.conversation_id);
      }

      // Add assistant message
      setLocalMessages((prev) => [...prev, response.message]);
    } catch (error) {
      // Add error message
      const errorMessage: AIMessageType = {
        id: Date.now() + 1,
        role: "assistant",
        content: "Sorry, I encountered an error processing your request.",
        error: error instanceof Error ? error.message : "Unknown error",
        created_at: new Date().toISOString(),
      };
      setLocalMessages((prev) => [...prev, errorMessage]);
    }
  };

  const handleNewConversation = () => {
    setCurrentConversationId(null);
    setLocalMessages([]);
  };

  const handleSelectConversation = (id: number) => {
    setCurrentConversationId(id);
    setLocalMessages([]);
  };

  const handleDeleteConversation = async (id: number) => {
    await deleteMutation.mutateAsync(id);
    if (currentConversationId === id) {
      handleNewConversation();
    }
  };

  const handleSelectSuggestion = (question: string) => {
    handleSendMessage(question);
  };

  const showWelcome = localMessages.length === 0 && !currentConversationId;

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden">
      {/* Sidebar */}
      <ChatSidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        isLoading={conversationsLoading}
      />

      {/* Main chat area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Messages */}
        <ScrollArea className="flex-1" ref={scrollRef}>
          <div className="max-w-4xl mx-auto">
            {showWelcome ? (
              <SuggestedQuestions
                suggestions={suggestions}
                onSelect={handleSelectSuggestion}
                isLoading={suggestionsLoading}
              />
            ) : (
              <div className="divide-y">
                {localMessages.map((message) => (
                  <AIMessage key={message.id} message={message} />
                ))}
                {askMutation.isPending && <ThinkingIndicator />}
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Input */}
        <div className="max-w-4xl mx-auto w-full">
          <ChatInput
            onSend={handleSendMessage}
            isLoading={askMutation.isPending}
            placeholder={
              showWelcome
                ? "Ask a question about your data..."
                : "Ask a follow-up question..."
            }
          />
        </div>
      </div>
    </div>
  );
}
