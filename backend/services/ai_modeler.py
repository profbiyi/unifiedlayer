"""
AI Modeler Service.

Uses OpenAI to automatically generate dimensional models (star schema)
from raw data schemas. Generates business questions, canonical models,
and dimensional models with SQL views.
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import uuid

from openai import OpenAI
from sqlalchemy.orm import Session

from backend.config import settings
from backend.services.openai_helper import chat_completion
from backend.database import get_db_session
from backend.services.schema_analyzer import SchemaContext, get_schema_analyzer
from backend.models.data_model import GeneratedModel, ModelLayer, ModelStatus

logger = logging.getLogger(__name__)


@dataclass
class ColumnDefinition:
    """Definition of a column in a generated model."""
    name: str
    data_type: str
    description: str
    source_column: Optional[str] = None


@dataclass
class ModelDefinition:
    """Definition of a generated model."""
    name: str
    description: str
    layer: str  # canonical or dimensional
    model_type: str  # fact, dimension, canonical
    columns: List[ColumnDefinition]
    source_tables: List[str]
    sql_definition: str
    business_questions: List[str] = field(default_factory=list)
    relationships: List[Dict[str, str]] = field(default_factory=list)
    ai_reasoning: str = ""


@dataclass
class ModelingResult:
    """Result of AI modeling."""
    business_questions: List[str]
    canonical_models: List[ModelDefinition]
    dimensional_models: List[ModelDefinition]
    error: Optional[str] = None


class AIModeler:
    """
    AI-powered dimensional modeling service.

    Uses OpenAI GPT-4o to analyze raw table schemas and generate:
    1. Business questions the data can answer
    2. Canonical (normalized, cleaned) models
    3. Dimensional models (fact and dimension tables)
    4. SQL views for each model
    """

    def __init__(self):
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            logger.warning("OPENAI_API_KEY not set - AI modeling will be unavailable")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)

        self.model = getattr(settings, "OPENAI_MODEL_ADVANCED", "gpt-4o")
        self.schema_analyzer = get_schema_analyzer()

    def analyze_schema(
        self,
        destination_config: Dict[str, Any],
        destination_type: str,
        tables: Optional[List[str]] = None,
        schema_name: Optional[str] = None,
    ) -> SchemaContext:
        """
        Analyze destination schema.

        Args:
            destination_config: Destination credentials and config
            destination_type: Type of destination (postgres, snowflake, etc.)
            tables: Specific tables to analyze (None = all)
            schema_name: Schema/dataset name

        Returns:
            SchemaContext with table information
        """
        self.schema_analyzer.connect(destination_config, destination_type)
        try:
            return self.schema_analyzer.analyze_tables(tables, schema_name)
        finally:
            self.schema_analyzer.close()

    def generate_business_questions(
        self,
        schema_context: SchemaContext,
        num_questions: int = 20
    ) -> List[str]:
        """
        Generate business questions that can be answered with this data.

        Args:
            schema_context: Schema context from analyze_schema()
            num_questions: Number of questions to generate

        Returns:
            List of business questions
        """
        if not self.client:
            logger.error("OpenAI client not configured")
            return []

        schema_summary = self.schema_analyzer.get_schema_summary(schema_context)

        system_prompt = """You are a business analyst specializing in data analytics.
Given a database schema, generate relevant business questions that can be answered using this data.

Focus on:
- Revenue and financial metrics
- Customer behavior and segments
- Operational efficiency
- Trends over time
- Key performance indicators (KPIs)

Output format: Return a JSON array of questions.
Example: ["What is the total revenue by month?", "Which customers have the highest lifetime value?"]
"""

        user_prompt = f"""
## Database Schema
{schema_summary}

## Task
Generate {num_questions} relevant business questions that can be answered using this data.
Consider the relationships between tables and the types of data available.

Return ONLY a JSON array of question strings.
"""

        try:
            response = chat_completion(self.client,
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            # Handle both {"questions": [...]} and direct array formats
            if isinstance(result, dict):
                questions = result.get("questions", result.get("business_questions", []))
            elif isinstance(result, list):
                questions = result
            else:
                questions = []

            logger.info(f"Generated {len(questions)} business questions")
            return questions[:num_questions]

        except Exception as e:
            logger.error(f"Failed to generate business questions: {e}")
            return []

    def generate_canonical_models(
        self,
        schema_context: SchemaContext
    ) -> List[ModelDefinition]:
        """
        Generate canonical (normalized, cleaned) models from raw data.

        Canonical models represent cleaned and standardized versions of the raw data,
        with proper naming, data types, and deduplication.

        Args:
            schema_context: Schema context from analyze_schema()

        Returns:
            List of canonical model definitions
        """
        if not self.client:
            logger.error("OpenAI client not configured")
            return []

        schema_summary = self.schema_analyzer.get_schema_summary(schema_context)

        system_prompt = """You are a senior data engineer specializing in data modeling.
Your task is to generate canonical (cleaned, normalized) models from raw data.

Canonical models should:
1. Have clean, descriptive column names (snake_case)
2. Have proper data types
3. Remove duplicates and handle nulls
4. Add surrogate keys where appropriate
5. Standardize formats (dates, currencies, etc.)

Output format: JSON with structure:
{
  "models": [
    {
      "name": "canonical_customers",
      "description": "Cleaned customer data",
      "source_tables": ["raw_customers"],
      "columns": [
        {"name": "customer_id", "data_type": "VARCHAR", "description": "Unique customer identifier", "source_column": "id"}
      ],
      "sql_definition": "CREATE VIEW canonical_customers AS SELECT ...",
      "ai_reasoning": "Why this model was created"
    }
  ]
}
"""

        user_prompt = f"""
## Raw Database Schema
{schema_summary}

## Task
Generate canonical models that clean and normalize this raw data.

For each raw table, create a canonical view that:
1. Renames columns to clear, descriptive names
2. Casts data types appropriately
3. Handles NULL values with COALESCE where needed
4. Adds computed columns if useful (e.g., full_name from first_name + last_name)

Use naming convention: canonical_<entity_name>

Generate CREATE VIEW statements compatible with PostgreSQL.
"""

        try:
            response = chat_completion(self.client,
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=4000,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)
            models_data = result.get("models", [])

            models = []
            for m in models_data:
                columns = [
                    ColumnDefinition(
                        name=c["name"],
                        data_type=c["data_type"],
                        description=c["description"],
                        source_column=c.get("source_column"),
                    )
                    for c in m.get("columns", [])
                ]

                models.append(ModelDefinition(
                    name=m["name"],
                    description=m["description"],
                    layer="canonical",
                    model_type="canonical",
                    columns=columns,
                    source_tables=m.get("source_tables", []),
                    sql_definition=m.get("sql_definition", ""),
                    ai_reasoning=m.get("ai_reasoning", ""),
                ))

            logger.info(f"Generated {len(models)} canonical models")
            return models

        except Exception as e:
            logger.error(f"Failed to generate canonical models: {e}")
            return []

    def generate_dimensional_models(
        self,
        schema_context: SchemaContext,
        canonical_models: Optional[List[ModelDefinition]] = None,
        business_questions: Optional[List[str]] = None
    ) -> List[ModelDefinition]:
        """
        Generate dimensional models (star schema) for analytics.

        Creates fact and dimension tables based on the data structure
        and business questions.

        Args:
            schema_context: Schema context from analyze_schema()
            canonical_models: Optional canonical models to build upon
            business_questions: Optional business questions to guide modeling

        Returns:
            List of dimensional model definitions (facts and dimensions)
        """
        if not self.client:
            logger.error("OpenAI client not configured")
            return []

        schema_summary = self.schema_analyzer.get_schema_summary(schema_context)

        # Build canonical models context
        canonical_context = ""
        if canonical_models:
            canonical_context = "\n## Canonical Models Available\n"
            for cm in canonical_models:
                canonical_context += f"- {cm.name}: {cm.description}\n"

        # Build business questions context
        questions_context = ""
        if business_questions:
            questions_context = "\n## Business Questions to Answer\n"
            for i, q in enumerate(business_questions[:10], 1):
                questions_context += f"{i}. {q}\n"

        system_prompt = """You are a senior data engineer specializing in dimensional modeling.
Your task is to generate a star schema (fact and dimension tables) for analytics.

Design principles:
1. Fact tables contain measurable events (transactions, orders, etc.)
2. Dimension tables contain descriptive attributes
3. Use surrogate keys for dimensions
4. Include date dimensions for time-based analysis
5. Denormalize for query performance

Naming conventions:
- Fact tables: fact_<name>
- Dimension tables: dim_<name>
- Use snake_case for all names

Output format: JSON with structure:
{
  "fact_tables": [
    {
      "name": "fact_orders",
      "description": "Order transactions",
      "source_tables": ["orders", "order_items"],
      "columns": [
        {"name": "order_key", "data_type": "BIGINT", "description": "Surrogate key"},
        {"name": "customer_key", "data_type": "BIGINT", "description": "FK to dim_customer"},
        {"name": "order_amount", "data_type": "DECIMAL(18,2)", "description": "Total order amount"}
      ],
      "sql_definition": "CREATE VIEW fact_orders AS SELECT ...",
      "business_questions": ["What is total revenue by month?"],
      "ai_reasoning": "Why this fact table was created"
    }
  ],
  "dimension_tables": [
    {
      "name": "dim_customer",
      "description": "Customer dimension",
      "source_tables": ["customers"],
      "columns": [...],
      "sql_definition": "CREATE VIEW dim_customer AS SELECT ...",
      "ai_reasoning": "Why this dimension was created"
    }
  ],
  "relationships": [
    {"fact": "fact_orders", "dimension": "dim_customer", "join_key": "customer_key"}
  ]
}
"""

        user_prompt = f"""
## Raw Database Schema
{schema_summary}
{canonical_context}
{questions_context}

## Task
Generate a star schema for analytics with:
1. Fact tables for measurable events (transactions, orders, etc.)
2. Dimension tables for descriptive attributes (customers, products, dates, etc.)
3. A date dimension (dim_date) for time-based analysis
4. SQL views that transform raw/canonical data into these models

Generate CREATE VIEW statements compatible with PostgreSQL.
Include appropriate JOINs and aggregations in fact tables.
"""

        try:
            response = chat_completion(self.client,
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=6000,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            models = []

            # Process fact tables
            for ft in result.get("fact_tables", []):
                columns = [
                    ColumnDefinition(
                        name=c["name"],
                        data_type=c["data_type"],
                        description=c["description"],
                        source_column=c.get("source_column"),
                    )
                    for c in ft.get("columns", [])
                ]

                # Find relationships for this fact table
                relationships = [
                    r for r in result.get("relationships", [])
                    if r.get("fact") == ft["name"]
                ]

                models.append(ModelDefinition(
                    name=ft["name"],
                    description=ft["description"],
                    layer="dimensional",
                    model_type="fact",
                    columns=columns,
                    source_tables=ft.get("source_tables", []),
                    sql_definition=ft.get("sql_definition", ""),
                    business_questions=ft.get("business_questions", []),
                    relationships=relationships,
                    ai_reasoning=ft.get("ai_reasoning", ""),
                ))

            # Process dimension tables
            for dt in result.get("dimension_tables", []):
                columns = [
                    ColumnDefinition(
                        name=c["name"],
                        data_type=c["data_type"],
                        description=c["description"],
                        source_column=c.get("source_column"),
                    )
                    for c in dt.get("columns", [])
                ]

                models.append(ModelDefinition(
                    name=dt["name"],
                    description=dt["description"],
                    layer="dimensional",
                    model_type="dimension",
                    columns=columns,
                    source_tables=dt.get("source_tables", []),
                    sql_definition=dt.get("sql_definition", ""),
                    ai_reasoning=dt.get("ai_reasoning", ""),
                ))

            logger.info(f"Generated {len(models)} dimensional models")
            return models

        except Exception as e:
            logger.error(f"Failed to generate dimensional models: {e}")
            return []

    def generate_sql_views(
        self,
        models: List[ModelDefinition],
        sql_dialect: str = "postgresql"
    ) -> Dict[str, str]:
        """
        Generate or refine SQL view definitions for models.

        Args:
            models: List of model definitions
            sql_dialect: Target SQL dialect

        Returns:
            Dictionary mapping model names to SQL definitions
        """
        sql_views = {}

        for model in models:
            if model.sql_definition:
                sql_views[model.name] = model.sql_definition
            else:
                # Generate a basic view structure
                columns_sql = ", ".join([
                    f"{col.source_column or col.name} AS {col.name}"
                    for col in model.columns
                ])
                source = model.source_tables[0] if model.source_tables else "unknown_table"
                sql_views[model.name] = f"CREATE OR REPLACE VIEW {model.name} AS SELECT {columns_sql} FROM {source};"

        return sql_views

    def auto_model_pipeline(
        self,
        pipeline_id: int,
        db: Optional[Session] = None
    ) -> ModelingResult:
        """
        Full auto-modeling pipeline for a data pipeline.

        1. Get pipeline destination config
        2. Analyze schema
        3. Generate business questions
        4. Generate canonical models
        5. Generate dimensional models
        6. Save all models to database

        Args:
            pipeline_id: Pipeline ID to model
            db: Optional database session

        Returns:
            ModelingResult with all generated content
        """
        from backend.models.pipeline import Pipeline

        close_db = False
        if db is None:
            db = get_db_session()
            close_db = True

        try:
            # Get pipeline
            pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
            if not pipeline:
                return ModelingResult(
                    business_questions=[],
                    canonical_models=[],
                    dimensional_models=[],
                    error=f"Pipeline {pipeline_id} not found",
                )

            destination = pipeline.destination
            if not destination:
                return ModelingResult(
                    business_questions=[],
                    canonical_models=[],
                    dimensional_models=[],
                    error="Pipeline has no destination configured",
                )

            logger.info(f"Auto-modeling pipeline {pipeline_id}: {pipeline.name}")

            # Analyze schema
            dataset_name = destination.config.get("dataset_name", "default")
            schema_context = self.analyze_schema(
                destination_config=destination.config,
                destination_type=destination.destination_type.value,
                schema_name=dataset_name,
            )

            if not schema_context.tables:
                return ModelingResult(
                    business_questions=[],
                    canonical_models=[],
                    dimensional_models=[],
                    error="No tables found in destination to model",
                )

            # Generate business questions
            logger.info("Generating business questions...")
            business_questions = self.generate_business_questions(schema_context)

            # Generate canonical models
            logger.info("Generating canonical models...")
            canonical_models = self.generate_canonical_models(schema_context)

            # Generate dimensional models
            logger.info("Generating dimensional models...")
            dimensional_models = self.generate_dimensional_models(
                schema_context,
                canonical_models,
                business_questions,
            )

            # Save models to database
            logger.info("Saving models to database...")
            for model in canonical_models + dimensional_models:
                self._save_model(
                    db=db,
                    organization_id=pipeline.organization_id,
                    pipeline_id=pipeline_id,
                    model=model,
                    business_questions=business_questions,
                )

            db.commit()

            logger.info(
                f"Auto-modeling complete: {len(canonical_models)} canonical, "
                f"{len(dimensional_models)} dimensional models"
            )

            return ModelingResult(
                business_questions=business_questions,
                canonical_models=canonical_models,
                dimensional_models=dimensional_models,
            )

        except Exception as e:
            logger.error(f"Auto-modeling failed: {e}", exc_info=True)
            if db:
                db.rollback()
            return ModelingResult(
                business_questions=[],
                canonical_models=[],
                dimensional_models=[],
                error=str(e),
            )
        finally:
            if close_db and db:
                db.close()

    def _save_model(
        self,
        db: Session,
        organization_id: int,
        pipeline_id: int,
        model: ModelDefinition,
        business_questions: List[str],
    ) -> GeneratedModel:
        """Save a model definition to the database."""
        # Map layer string to enum
        layer_map = {
            "canonical": ModelLayer.CANONICAL,
            "dimensional": ModelLayer.DIMENSIONAL,
            "raw": ModelLayer.RAW,
        }
        layer = layer_map.get(model.layer, ModelLayer.DIMENSIONAL)

        # Build columns JSON
        columns_json = [
            {
                "name": col.name,
                "type": col.data_type,
                "description": col.description,
                "source_column": col.source_column,
            }
            for col in model.columns
        ]

        # Filter relevant business questions for this model
        model_questions = model.business_questions or []
        if not model_questions and model.model_type == "fact":
            # Assign some questions to fact tables
            model_questions = business_questions[:5]

        db_model = GeneratedModel(
            public_id=uuid.uuid4(),
            organization_id=organization_id,
            pipeline_id=pipeline_id,
            name=model.name,
            description=model.description,
            layer=layer,
            model_type=model.model_type,
            source_tables=model.source_tables,
            sql_definition=model.sql_definition,
            columns=columns_json,
            relationships=model.relationships,
            business_questions=model_questions,
            ai_reasoning=model.ai_reasoning,
            status=ModelStatus.DRAFT,
            is_materialized=False,
        )

        db.add(db_model)
        db.flush()

        logger.info(f"Saved model: {model.name} (id={db_model.id})")
        return db_model


def get_ai_modeler() -> AIModeler:
    """Factory function for AIModeler."""
    return AIModeler()
