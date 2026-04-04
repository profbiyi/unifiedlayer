export interface Pipeline {
  id: string;
  name: string;
  description?: string;
  source_id: string;
  destination_id: string;
  schedule?: string;
  max_retries?: number;
  retry_delay_seconds?: number;
  exponential_backoff_enabled?: boolean;
  is_active: boolean;
  write_mode?: WriteMode;
  schema_contract?: SchemaContract;
  created_at: string;
  updated_at: string;
  source?: Source;
  destination?: Destination;
}

export type WriteMode = 'append' | 'merge' | 'upsert' | 'insert_only' | 'scd2' | 'replace';
export type SchemaContract = 'evolve' | 'freeze' | 'discard_columns' | 'discard_rows';

export interface Source {
  id: string;
  name: string;
  description?: string;
  type: string;
  source_type: string;
  config: Record<string, any>;
  is_active: boolean;
  organization_id: number;
  created_at: string;
  updated_at: string;
}

export interface Destination {
  id: string;
  name: string;
  description?: string;
  type: string;
  destination_type: string;
  config: Record<string, any>;
  is_active: boolean;
  organization_id: number;
  created_at: string;
  updated_at: string;
}

export interface PipelineRun {
  id: string;
  pipeline_id: string;
  pipeline_name?: string;
  public_id?: string;
  status: "pending" | "running" | "completed" | "failed";
  retry_count?: number;
  is_retry?: boolean;
  original_run_id?: number;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  error_traceback?: string;
  rows_read?: number;
  rows_written?: number;
  bytes_read?: number;
  bytes_written?: number;
  duration_seconds?: number;
  run_metadata?: Record<string, any>;  // Changed from 'metadata' to match backend
  created_at: string;
}

export interface TransformationConfig {
  column_mapping?: Record<string, string>;
  excluded_columns?: string[];
  type_casts?: Record<string, string>;
  filters?: Array<{
    column: string;
    operator: "=" | "!=" | ">" | "<" | "contains";
    value: string;
  }>;
}

export interface CreatePipelineRequest {
  name: string;
  description?: string;
  source_id: string;
  destination_id: string;
  schedule?: string;
  is_active: boolean;
  write_mode?: WriteMode;
  schema_contract?: SchemaContract;
  config?: {
    transformations?: TransformationConfig;
  };
}

export interface UpdatePipelineRequest {
  name?: string;
  description?: string;
  source_id?: string;
  destination_id?: string;
  schedule?: string;
  is_active?: boolean;
  write_mode?: WriteMode;
  schema_contract?: SchemaContract;
}
