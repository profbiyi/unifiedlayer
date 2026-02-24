/**
 * AI-Generated Dimensional Model Types
 */

export type ModelLayer = "raw" | "canonical" | "dimensional";

export interface ModelColumn {
  name: string;
  type: string;
  description: string;
}

export interface ModelRelationship {
  from_column: string;
  to_table: string;
  to_column: string;
}

export interface GeneratedModel {
  id: string;
  name: string;
  description: string;
  layer: ModelLayer;
  source_tables: string[];
  sql_definition: string;
  columns: ModelColumn[];
  relationships: ModelRelationship[];
  business_questions: string[];
  ai_reasoning: string;
  is_materialized: boolean;
  pipeline_id: string;
  created_at: string;
}

export interface ModelGenerationResult {
  models: GeneratedModel[];
  fact_tables: number;
  dimension_tables: number;
  questions_generated: number;
}

export interface GenerateModelsRequest {
  pipeline_id: string;
}

export interface MaterializeModelRequest {
  create_view: boolean;
}

export interface MaterializeModelResult {
  success: boolean;
  view_name: string;
  message: string;
}
