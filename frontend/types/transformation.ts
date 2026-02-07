/**
 * SQL Transformation Types
 */

export type TransformationStatus = "pending" | "running" | "completed" | "failed" | "skipped";

export type WriteMode = "replace" | "append" | "merge";

export interface SQLTransformation {
  id: string;
  pipeline_id: string;
  name: string;
  description?: string;
  sql_query: string;
  target_table?: string;
  write_mode: WriteMode;
  execution_order: number;
  is_active: boolean;
  continue_on_error: boolean;
  timeout_seconds: number;
  created_at: string;
  updated_at: string;
}

export interface CreateTransformationRequest {
  name: string;
  description?: string;
  sql_query: string;
  target_table?: string;
  write_mode?: WriteMode;
  execution_order?: number;
  is_active?: boolean;
  continue_on_error?: boolean;
  timeout_seconds?: number;
}

export interface UpdateTransformationRequest {
  name?: string;
  description?: string;
  sql_query?: string;
  target_table?: string;
  write_mode?: WriteMode;
  execution_order?: number;
  is_active?: boolean;
  continue_on_error?: boolean;
  timeout_seconds?: number;
}

export interface ReorderTransformationsRequest {
  transformation_ids: string[];
}

export interface TransformationResult {
  id: string;
  pipeline_run_id: string;
  transformation_id: string;
  status: TransformationStatus;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  rows_affected?: number;
  error_message?: string;
  error_traceback?: string;
  result_metadata?: Record<string, any>;
  created_at: string;
}

export interface SQLPreviewRequest {
  sql_query: string;
  limit?: number;
}

export interface SQLPreviewResult {
  columns: string[];
  rows: Record<string, any>[];
  row_count: number;
  execution_time_ms: number;
  error?: string;
  error_traceback?: string;
}
