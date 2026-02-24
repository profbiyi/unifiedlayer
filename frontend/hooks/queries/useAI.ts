/**
 * AI Assistant API Hooks
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api-client";
import type {
  AIConversation,
  AIConversationDetail,
  AskRequest,
  AskResponse,
  SuggestedQuestion,
} from "@/types/ai";

// Query keys
export const aiKeys = {
  all: ["ai"] as const,
  conversations: () => [...aiKeys.all, "conversations"] as const,
  conversation: (id: number) => [...aiKeys.all, "conversation", id] as const,
  suggestions: () => [...aiKeys.all, "suggestions"] as const,
};

/**
 * Ask a question to the AI assistant
 */
export function useAskQuestion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: AskRequest): Promise<AskResponse> => {
      const response = await apiClient.post("/ai/ask", data);
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidate conversations list to update message count
      queryClient.invalidateQueries({ queryKey: aiKeys.conversations() });
      // Update the specific conversation if it exists
      if (data.conversation_id) {
        queryClient.invalidateQueries({
          queryKey: aiKeys.conversation(data.conversation_id),
        });
      }
    },
  });
}

/**
 * List all conversations
 */
export function useConversations(limit: number = 50) {
  return useQuery({
    queryKey: aiKeys.conversations(),
    queryFn: async (): Promise<AIConversation[]> => {
      const response = await apiClient.get(`/ai/conversations?limit=${limit}`);
      return response.data;
    },
  });
}

/**
 * Get a single conversation with all messages
 */
export function useConversation(id: number | null) {
  return useQuery({
    queryKey: aiKeys.conversation(id!),
    queryFn: async (): Promise<AIConversationDetail> => {
      const response = await apiClient.get(`/ai/conversations/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

/**
 * Delete a conversation
 */
export function useDeleteConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      await apiClient.delete(`/ai/conversations/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aiKeys.conversations() });
    },
  });
}

/**
 * Get suggested questions based on connected sources
 */
export function useSuggestedQuestions() {
  return useQuery({
    queryKey: aiKeys.suggestions(),
    queryFn: async (): Promise<SuggestedQuestion[]> => {
      const response = await apiClient.get("/ai/suggestions");
      return response.data;
    },
  });
}
