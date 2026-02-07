export type DbtRunStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface DbtProject {
  id: string;
  name: string;
  description?: string;
  git_repo_url: string;
  git_branch: string;
  git_username?: string;
  target_profile: string;
  default_models?: string[];
  is_active: boolean;
  organization_id: number;
  created_at: string;
  updated_at: string;
  last_run?: DbtRun;
}

export interface DbtRun {
  id: string;
  project_id: string;
  status: DbtRunStatus;
  models: string[];
  full_refresh: boolean;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  models_executed?: DbtModelExecution[];
  logs?: string;
  error_message?: string;
  created_at: string;
}

export interface DbtModelExecution {
  model_name: string;
  status: "success" | "error" | "skipped";
  rows_affected?: number;
  duration_seconds?: number;
  error_message?: string;
}

export interface CreateDbtProjectRequest {
  name: string;
  description?: string;
  git_repo_url: string;
  git_branch: string;
  git_username?: string;
  git_token?: string;
  target_profile: string;
  default_models?: string[];
}

export interface UpdateDbtProjectRequest {
  name?: string;
  description?: string;
  git_repo_url?: string;
  git_branch?: string;
  git_username?: string;
  git_token?: string;
  target_profile?: string;
  default_models?: string[];
  is_active?: boolean;
}

export interface TriggerDbtRunRequest {
  models?: string[];
  full_refresh?: boolean;
}

export interface DbtPipelineConfig {
  project_id: string;
  models: string[];
  full_refresh: boolean;
  run_on_success: boolean;
  fail_pipeline_on_error: boolean;
}

export interface TestConnectionResponse {
  success: boolean;
  message: string;
  branches?: string[];
}
