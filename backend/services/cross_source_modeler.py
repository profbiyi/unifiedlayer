"""
Cross-Source Modeler Service.

Analyzes data across multiple sources to detect relationships and generate
unified dimensional models that combine data from different sources.

This enables rich analytics like:
- Stripe customers + CRM data + Xero invoices = Full customer 360 view
- Paystack transactions + Internal orders = Complete order analytics
"""
import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import uuid

from openai import OpenAI
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.pipeline import Pipeline
from backend.models.data_model import GeneratedModel, ModelLayer, ModelStatus
from backend.services.schema_analyzer import SchemaContext, TableSchema, get_schema_analyzer
from backend.services.ai_modeler import AIModeler

logger = logging.getLogger(__name__)


@dataclass
class CrossSourceColumn:
    """A column that could be used for cross-source joins."""
    source_name: str
    table_name: str
    column_name: str
    data_type: str
    sample_values: List[str]


@dataclass
class SuggestedJoin:
    """An AI-suggested join between two sources."""
    id: str
    left_source: str
    left_table: str
    left_column: str
    right_source: str
    right_table: str
    right_column: str
    confidence: float  # 0-1 confidence score
    reasoning: str
    join_type: str  # "exact", "fuzzy", "derived"
    sample_matches: List[Tuple[str, str]]  # Sample matching values


@dataclass
class EnrichmentConfig:
    """User-confirmed enrichment configuration."""
    confirmed_joins: List[SuggestedJoin]
    custom_joins: List[Dict[str, str]]  # User-defined joins
    primary_source: str  # Which source is the "main" one
    enrichment_sources: List[str]  # Sources to enrich from


@dataclass
class CrossSourceSchema:
    """Combined schema from multiple sources."""
    sources: Dict[str, SchemaContext]  # source_name -> schema
    all_tables: List[Tuple[str, TableSchema]]  # (source_name, table)
    suggested_joins: List[SuggestedJoin]


class CrossSourceModeler:
    """
    Cross-source modeling service.

    Analyzes multiple data sources together to:
    1. Detect relationships across sources
    2. Suggest join keys (email, customer_id, etc.)
    3. Generate unified dimensional models
    """

    # Common join patterns to look for
    JOIN_PATTERNS = {
        "email": ["email", "email_address", "user_email", "customer_email", "contact_email"],
        "customer_id": ["customer_id", "cust_id", "client_id", "user_id", "account_id"],
        "phone": ["phone", "phone_number", "mobile", "tel", "telephone"],
        "name": ["name", "full_name", "customer_name", "company_name", "account_name"],
        "external_id": ["external_id", "ext_id", "reference", "ref", "stripe_id", "paystack_id", "xero_id"],
        "order_id": ["order_id", "invoice_id", "transaction_id", "payment_id"],
        "date": ["date", "created_at", "created_date", "transaction_date", "invoice_date"],
    }

    def __init__(self):
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            logger.warning("OPENAI_API_KEY not set - Cross-source modeling will be limited")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)

        self.model = "gpt-4o"
        self.schema_analyzer = get_schema_analyzer()
        self.ai_modeler = AIModeler()

    def get_org_sources_schemas(
        self,
        db: Session,
        org_id: int,
        source_ids: Optional[List[int]] = None,
    ) -> CrossSourceSchema:
        """
        Get schemas from all (or selected) sources for an organization.

        Args:
            db: Database session
            org_id: Organization ID
            source_ids: Optional list of specific source IDs to analyze

        Returns:
            CrossSourceSchema with combined information
        """
        # Get all pipelines for the org (to find destinations with data)
        query = db.query(Pipeline).filter(
            Pipeline.organization_id == org_id,
            Pipeline.is_active,
        )

        pipelines = query.all()

        if not pipelines:
            logger.warning(f"No active pipelines found for org {org_id}")
            return CrossSourceSchema(sources={}, all_tables=[], suggested_joins=[])

        sources_schemas: Dict[str, SchemaContext] = {}
        all_tables: List[Tuple[str, TableSchema]] = []

        # Group pipelines by destination to avoid duplicate connections
        destinations_seen = set()

        for pipeline in pipelines:
            if source_ids and pipeline.source_id not in source_ids:
                continue

            dest = pipeline.destination
            source = pipeline.source

            if not dest or not source:
                continue

            # Skip if we've already analyzed this destination
            if dest.id in destinations_seen:
                continue
            destinations_seen.add(dest.id)

            try:
                # Connect to destination and get schema
                self.schema_analyzer.connect(dest.config, dest.destination_type.value)
                schema_context = self.schema_analyzer.analyze_tables()

                source_name = source.name or f"source_{source.id}"
                sources_schemas[source_name] = schema_context

                # Add tables with source name
                for table in schema_context.tables:
                    all_tables.append((source_name, table))

                logger.info(f"Analyzed {len(schema_context.tables)} tables from {source_name}")

            except Exception as e:
                logger.error(f"Failed to analyze source {source.name}: {e}")
            finally:
                self.schema_analyzer.close()

        # Detect cross-source relationships
        suggested_joins = self._detect_cross_source_joins(sources_schemas)

        return CrossSourceSchema(
            sources=sources_schemas,
            all_tables=all_tables,
            suggested_joins=suggested_joins,
        )

    def _detect_cross_source_joins(
        self,
        sources_schemas: Dict[str, SchemaContext],
    ) -> List[SuggestedJoin]:
        """
        Detect potential join keys across sources using pattern matching.

        Looks for:
        1. Exact column name matches (email = email)
        2. Pattern matches (customer_email matches contact_email)
        3. Sample value overlaps
        """
        suggested_joins: List[SuggestedJoin] = []

        # Build index of columns by pattern
        columns_by_pattern: Dict[str, List[CrossSourceColumn]] = {}

        for source_name, schema in sources_schemas.items():
            for table in schema.tables:
                for column in table.columns:
                    col_lower = column.name.lower()

                    # Check which pattern this column matches
                    for pattern_name, pattern_variants in self.JOIN_PATTERNS.items():
                        if any(variant in col_lower for variant in pattern_variants):
                            if pattern_name not in columns_by_pattern:
                                columns_by_pattern[pattern_name] = []

                            # Get sample values for this column
                            sample_values = []
                            if table.sample_data:
                                for row in table.sample_data[:5]:
                                    if column.name in row and row[column.name]:
                                        sample_values.append(str(row[column.name]))

                            columns_by_pattern[pattern_name].append(CrossSourceColumn(
                                source_name=source_name,
                                table_name=table.name,
                                column_name=column.name,
                                data_type=column.data_type,
                                sample_values=sample_values,
                            ))
                            break

        # Find cross-source matches
        for pattern_name, columns in columns_by_pattern.items():
            # Group by source
            by_source: Dict[str, List[CrossSourceColumn]] = {}
            for col in columns:
                if col.source_name not in by_source:
                    by_source[col.source_name] = []
                by_source[col.source_name].append(col)

            # Only interesting if multiple sources have this pattern
            if len(by_source) < 2:
                continue

            # Generate join suggestions between sources
            source_names = list(by_source.keys())
            for i, source1 in enumerate(source_names):
                for source2 in source_names[i+1:]:
                    for col1 in by_source[source1]:
                        for col2 in by_source[source2]:
                            # Calculate confidence based on:
                            # 1. Name similarity
                            # 2. Data type match
                            # 3. Sample value overlap
                            confidence = self._calculate_join_confidence(col1, col2)

                            if confidence > 0.5:  # Only suggest high-confidence joins
                                # Find sample matches
                                sample_matches = []
                                for v1 in col1.sample_values:
                                    if v1 in col2.sample_values:
                                        sample_matches.append((v1, v1))

                                suggested_joins.append(SuggestedJoin(
                                    id=str(uuid.uuid4()),
                                    left_source=col1.source_name,
                                    left_table=col1.table_name,
                                    left_column=col1.column_name,
                                    right_source=col2.source_name,
                                    right_table=col2.table_name,
                                    right_column=col2.column_name,
                                    confidence=confidence,
                                    reasoning=f"Both columns match '{pattern_name}' pattern",
                                    join_type="exact" if col1.column_name.lower() == col2.column_name.lower() else "pattern",
                                    sample_matches=sample_matches[:3],
                                ))

        # Sort by confidence
        suggested_joins.sort(key=lambda x: x.confidence, reverse=True)

        logger.info(f"Found {len(suggested_joins)} potential cross-source joins")
        return suggested_joins

    def _calculate_join_confidence(
        self,
        col1: CrossSourceColumn,
        col2: CrossSourceColumn,
    ) -> float:
        """Calculate confidence score for a potential join."""
        score = 0.0

        # Exact name match
        if col1.column_name.lower() == col2.column_name.lower():
            score += 0.4
        else:
            # Partial name similarity
            name1_parts = set(col1.column_name.lower().split('_'))
            name2_parts = set(col2.column_name.lower().split('_'))
            overlap = len(name1_parts & name2_parts) / max(len(name1_parts | name2_parts), 1)
            score += 0.2 * overlap

        # Data type compatibility
        type1 = col1.data_type.upper()
        type2 = col2.data_type.upper()
        if type1 == type2:
            score += 0.3
        elif self._types_compatible(type1, type2):
            score += 0.15

        # Sample value overlap
        if col1.sample_values and col2.sample_values:
            set1 = set(col1.sample_values)
            set2 = set(col2.sample_values)
            if set1 & set2:
                overlap_ratio = len(set1 & set2) / min(len(set1), len(set2))
                score += 0.3 * overlap_ratio

        return min(score, 1.0)

    def _types_compatible(self, type1: str, type2: str) -> bool:
        """Check if two SQL types are compatible for joining."""
        string_types = {"VARCHAR", "TEXT", "CHAR", "STRING", "CHARACTER VARYING"}
        int_types = {"INT", "INTEGER", "BIGINT", "SMALLINT", "INT4", "INT8"}

        type1_upper = type1.upper().split("(")[0]
        type2_upper = type2.upper().split("(")[0]

        return (
            (type1_upper in string_types and type2_upper in string_types) or
            (type1_upper in int_types and type2_upper in int_types)
        )

    def enhance_joins_with_ai(
        self,
        cross_schema: CrossSourceSchema,
    ) -> List[SuggestedJoin]:
        """
        Use AI to enhance and validate suggested joins.

        AI can:
        1. Identify additional relationships
        2. Validate suggested joins
        3. Suggest fuzzy matching rules
        """
        if not self.client:
            return cross_schema.suggested_joins

        # Build schema summary for AI
        schema_summary = []
        for source_name, schema in cross_schema.sources.items():
            schema_summary.append(f"\n### Source: {source_name}")
            for table in schema.tables:
                cols = [f"{c.name} ({c.data_type})" for c in table.columns[:10]]
                schema_summary.append(f"Table {table.name}: {', '.join(cols)}")

        schema_text = "\n".join(schema_summary)

        # Existing suggestions
        existing = []
        for join in cross_schema.suggested_joins[:10]:
            existing.append(
                f"- {join.left_source}.{join.left_table}.{join.left_column} = "
                f"{join.right_source}.{join.right_table}.{join.right_column} "
                f"(confidence: {join.confidence:.2f})"
            )
        existing_text = "\n".join(existing) if existing else "None detected"

        system_prompt = """You are a data integration expert.
Given schemas from multiple data sources, identify relationships that can be used to join data across sources.

Look for:
1. Direct key matches (customer_id = customer_id)
2. Indirect matches (email addresses, phone numbers)
3. Business relationships (order -> customer via customer_id)

Output JSON format:
{
  "additional_joins": [
    {
      "left_source": "stripe",
      "left_table": "customers",
      "left_column": "email",
      "right_source": "crm",
      "right_table": "contacts",
      "right_column": "email_address",
      "confidence": 0.9,
      "reasoning": "Both contain customer email addresses"
    }
  ],
  "validation": [
    {"join_index": 0, "valid": true, "notes": "Good match"}
  ]
}
"""

        user_prompt = f"""
## Data Sources Schema
{schema_text}

## Already Detected Joins
{existing_text}

## Task
1. Identify additional cross-source relationships not already detected
2. Validate the existing join suggestions
3. Focus on relationships useful for customer analytics and business reporting

Return JSON with additional_joins and validation arrays.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            # Add AI-suggested joins
            additional = result.get("additional_joins", [])
            for aj in additional:
                cross_schema.suggested_joins.append(SuggestedJoin(
                    id=str(uuid.uuid4()),
                    left_source=aj["left_source"],
                    left_table=aj["left_table"],
                    left_column=aj["left_column"],
                    right_source=aj["right_source"],
                    right_table=aj["right_table"],
                    right_column=aj["right_column"],
                    confidence=aj.get("confidence", 0.7),
                    reasoning=aj.get("reasoning", "AI-suggested"),
                    join_type="ai_detected",
                    sample_matches=[],
                ))

            logger.info(f"AI added {len(additional)} additional join suggestions")
            return cross_schema.suggested_joins

        except Exception as e:
            logger.error(f"AI join enhancement failed: {e}")
            return cross_schema.suggested_joins

    def generate_unified_models(
        self,
        db: Session,
        org_id: int,
        cross_schema: CrossSourceSchema,
        enrichment_config: EnrichmentConfig,
    ) -> List[GeneratedModel]:
        """
        Generate unified dimensional models that combine multiple sources.

        Args:
            db: Database session
            org_id: Organization ID
            cross_schema: Combined schema from multiple sources
            enrichment_config: User-confirmed joins and settings

        Returns:
            List of generated unified models
        """
        if not self.client:
            logger.error("OpenAI client not configured")
            return []

        # Build comprehensive schema summary
        schema_parts = []
        for source_name, schema in cross_schema.sources.items():
            is_primary = source_name == enrichment_config.primary_source
            label = "(PRIMARY)" if is_primary else "(ENRICHMENT)"
            schema_parts.append(f"\n### Source: {source_name} {label}")

            summary = self.schema_analyzer.get_schema_summary(schema)
            schema_parts.append(summary)

        schema_text = "\n".join(schema_parts)

        # Build joins configuration
        joins_text = []
        for join in enrichment_config.confirmed_joins:
            joins_text.append(
                f"- JOIN {join.left_source}.{join.left_table} "
                f"ON {join.left_column} = {join.right_source}.{join.right_table}.{join.right_column}"
            )
        joins_config = "\n".join(joins_text) if joins_text else "No joins configured"

        system_prompt = """You are a senior data architect specializing in dimensional modeling.
Your task is to create UNIFIED dimensional models that combine data from multiple sources.

Create a star schema that:
1. Uses the PRIMARY source as the base for fact tables
2. Enriches with data from other sources via the specified joins
3. Creates dimension tables that merge related data across sources
4. Handles missing data gracefully with LEFT JOINs

Output JSON format:
{
  "models": [
    {
      "name": "dim_customers_unified",
      "description": "Unified customer dimension combining CRM, Stripe, and Xero data",
      "model_type": "dimension",
      "source_tables": ["stripe.customers", "crm.contacts", "xero.contacts"],
      "columns": [
        {"name": "customer_key", "data_type": "SERIAL", "description": "Surrogate key"},
        {"name": "email", "data_type": "VARCHAR", "description": "Customer email (from Stripe)"},
        {"name": "crm_segment", "data_type": "VARCHAR", "description": "Customer segment (from CRM)"},
        {"name": "xero_contact_id", "data_type": "VARCHAR", "description": "Xero contact reference"}
      ],
      "sql_definition": "CREATE VIEW dim_customers_unified AS SELECT ...",
      "ai_reasoning": "Combined customer data from all sources using email as the join key"
    }
  ]
}

Naming conventions:
- Fact tables: fact_<name>_unified
- Dimension tables: dim_<name>_unified
- Use snake_case
"""

        user_prompt = f"""
## Multi-Source Schema
{schema_text}

## Confirmed Join Keys
{joins_config}

## Primary Source: {enrichment_config.primary_source}
## Enrichment Sources: {', '.join(enrichment_config.enrichment_sources)}

## Task
Generate unified dimensional models that:
1. Create a comprehensive customer dimension (dim_customers_unified) merging customer data from all sources
2. Create fact tables for key metrics (transactions, orders, etc.)
3. Create date dimensions if date fields are present
4. Use LEFT JOINs so data doesn't disappear if enrichment sources don't match

Generate PostgreSQL-compatible CREATE VIEW statements.
"""

        try:
            response = self.client.chat.completions.create(
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

            # Save models to database
            saved_models = []
            for m in models_data:
                model = GeneratedModel(
                    public_id=uuid.uuid4(),
                    organization_id=org_id,
                    pipeline_id=None,  # Cross-source models aren't tied to one pipeline
                    name=m["name"],
                    description=m["description"],
                    layer=ModelLayer.DIMENSIONAL,
                    model_type=m.get("model_type", "unified"),
                    source_tables=m.get("source_tables", []),
                    sql_definition=m.get("sql_definition", ""),
                    columns=[{
                        "name": c["name"],
                        "data_type": c["data_type"],
                        "description": c["description"],
                    } for c in m.get("columns", [])],
                    relationships=[],
                    business_questions=[],
                    ai_reasoning=m.get("ai_reasoning", ""),
                    status=ModelStatus.DRAFT,
                    is_materialized=False,
                )

                db.add(model)
                saved_models.append(model)

            db.commit()
            for m in saved_models:
                db.refresh(m)

            logger.info(f"Generated {len(saved_models)} unified cross-source models")
            return saved_models

        except Exception as e:
            logger.error(f"Failed to generate unified models: {e}")
            db.rollback()
            return []


def get_cross_source_modeler() -> CrossSourceModeler:
    """Factory function for CrossSourceModeler."""
    return CrossSourceModeler()
