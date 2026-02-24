"""
Natural Language to SQL Service.

Uses LLM (OpenAI/Claude) to convert natural language questions to SQL queries.
"""
import json
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from openai import OpenAI

from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SQLGenerationResult:
    """Result of SQL generation from natural language."""
    sql: str
    explanation: str
    chart_suggestion: str  # "line", "bar", "pie", "number", "table"
    confidence: float  # 0.0 to 1.0
    error: Optional[str] = None


class NLToSQLService:
    """
    Service for converting natural language questions to SQL queries.

    Uses OpenAI GPT to understand questions and generate appropriate SQL.
    """

    def __init__(self):
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            logger.warning("OPENAI_API_KEY not set - AI features will be unavailable")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)

        self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')

    def _build_system_prompt(self, schema_context: str) -> str:
        """Build the system prompt for SQL generation."""
        return f"""You are a SQL expert assistant for a data analytics platform. Your job is to convert natural language questions into PostgreSQL queries.

{schema_context}

IMPORTANT RULES:
1. Only generate SELECT queries - never INSERT, UPDATE, DELETE, DROP, or any DDL
2. Always use proper PostgreSQL syntax
3. Include appropriate WHERE clauses to filter data
4. Use date functions like DATE_TRUNC, EXTRACT, NOW(), INTERVAL
5. For monetary amounts stored in cents, divide by 100.0 for display
6. Always add LIMIT if not specified (max 1000 rows)
7. Use meaningful column aliases for clarity
8. Handle NULL values appropriately with COALESCE

RESPONSE FORMAT:
You must respond with valid JSON only:
{{
    "sql": "SELECT ... FROM ... WHERE ...",
    "explanation": "Brief explanation of what this query does",
    "chart_suggestion": "line|bar|pie|number|table",
    "confidence": 0.95
}}

Chart suggestion guidelines:
- "number": Single value results (totals, counts, averages)
- "line": Time series data (revenue over time, trends)
- "bar": Categorical comparisons (revenue by product, top customers)
- "pie": Distribution/percentage data (payment methods, status breakdown)
- "table": Detailed lists, multiple columns, or when unsure

If you cannot generate a valid query, respond with:
{{
    "sql": "",
    "explanation": "Explain why you cannot generate the query",
    "chart_suggestion": "table",
    "confidence": 0.0,
    "error": "Brief error description"
}}"""

    async def generate_sql(
        self,
        question: str,
        schema_context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        dialect: str = "postgresql",
    ) -> SQLGenerationResult:
        """
        Generate SQL from a natural language question.

        Args:
            question: The user's question
            schema_context: Schema description from SchemaContextService
            conversation_history: Previous messages for context
            dialect: SQL dialect (currently only postgresql supported)

        Returns:
            SQLGenerationResult with generated SQL and metadata
        """
        if not self.client:
            return SQLGenerationResult(
                sql="",
                explanation="AI features are not available. Please configure OPENAI_API_KEY.",
                chart_suggestion="table",
                confidence=0.0,
                error="OPENAI_API_KEY not configured",
            )

        try:
            # Build messages
            messages = [
                {"role": "system", "content": self._build_system_prompt(schema_context)}
            ]

            # Add conversation history for context
            if conversation_history:
                for msg in conversation_history[-6:]:  # Last 6 messages for context
                    messages.append(msg)

            # Add the current question
            messages.append({"role": "user", "content": question})

            # Call OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,  # Low temperature for consistent SQL
                max_tokens=1000,
                response_format={"type": "json_object"},
            )

            # Parse response
            content = response.choices[0].message.content
            result = json.loads(content)

            return SQLGenerationResult(
                sql=result.get("sql", ""),
                explanation=result.get("explanation", ""),
                chart_suggestion=result.get("chart_suggestion", "table"),
                confidence=float(result.get("confidence", 0.5)),
                error=result.get("error"),
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return SQLGenerationResult(
                sql="",
                explanation="Failed to parse AI response",
                chart_suggestion="table",
                confidence=0.0,
                error=f"JSON parse error: {str(e)}",
            )

        except Exception as e:
            logger.error(f"LLM query failed: {e}")
            return SQLGenerationResult(
                sql="",
                explanation=f"AI query failed: {str(e)}",
                chart_suggestion="table",
                confidence=0.0,
                error=str(e),
            )

    def generate_title(self, question: str) -> str:
        """
        Generate a short title for a conversation based on the first question.

        Args:
            question: The first question in the conversation

        Returns:
            A short title (max 50 characters)
        """
        # Simple title generation without LLM call
        # Extract key words from the question
        question = question.strip()

        # Remove common question words
        for word in ["what", "how", "show", "give", "tell", "can", "could", "would", "please", "me", "my", "the", "is", "are", "was", "were"]:
            question = re.sub(rf"\b{word}\b", "", question, flags=re.IGNORECASE)

        # Clean up
        question = " ".join(question.split())

        # Truncate
        if len(question) > 50:
            question = question[:47] + "..."

        return question.strip() or "New conversation"


def get_nl_to_sql_service() -> NLToSQLService:
    """Factory function for NLToSQLService."""
    return NLToSQLService()
