/**
 * AI Assistant Types
 */

export interface ChartConfig {
  type: "line" | "bar" | "pie" | "number" | "table";
  title?: string;
  x_axis?: string;
  y_axis?: string | string[];
  format?: Record<string, string>;
  colors?: Record<string, string>;
}

export interface AIMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  sql?: string;
  results?: Record<string, unknown>[];
  row_count?: number;
  chart_config?: ChartConfig;
  execution_time_ms?: number;
  error?: string;
  created_at: string;
}

export interface AIConversation {
  id: number;
  title: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface AIConversationDetail {
  id: number;
  title: string | null;
  messages: AIMessage[];
  created_at: string;
  updated_at: string;
}

export interface AskRequest {
  question: string;
  conversation_id?: number;
}

export interface AskResponse {
  conversation_id: number;
  message: AIMessage;
}

export interface SuggestedQuestion {
  question: string;
  category: string;
}
