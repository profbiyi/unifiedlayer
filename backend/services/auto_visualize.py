"""
Auto Visualization Service.

Detects the best visualization type for query results.
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import re

logger = logging.getLogger(__name__)


@dataclass
class ChartConfig:
    """Configuration for chart visualization."""
    type: str  # "line", "bar", "pie", "number", "table"
    title: Optional[str] = None
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    colors: Optional[Dict[str, str]] = None
    format: Optional[Dict[str, str]] = None  # {"revenue": "currency", "date": "date"}
    stacked: bool = False


class AutoVisualizer:
    """
    Automatically detects the best visualization for query results.

    Rules:
    - Single row, single numeric column -> Big Number
    - Date/time column + numeric -> Line Chart
    - Categorical + numeric (few categories) -> Bar Chart
    - Multiple categories summing to ~100% -> Pie Chart
    - Everything else -> Table
    """

    # Column name patterns for detection
    DATE_PATTERNS = [
        r"date", r"time", r"day", r"week", r"month", r"year",
        r"created", r"updated", r"timestamp", r"period",
    ]

    NUMERIC_PATTERNS = [
        r"amount", r"total", r"sum", r"count", r"avg", r"revenue",
        r"sales", r"value", r"price", r"cost", r"balance", r"mrr",
        r"percent", r"rate", r"number", r"qty", r"quantity",
    ]

    CATEGORICAL_PATTERNS = [
        r"name", r"type", r"category", r"status", r"method",
        r"customer", r"product", r"channel", r"bucket", r"region",
    ]

    CURRENCY_PATTERNS = [
        r"amount", r"total", r"revenue", r"sales", r"value", r"price",
        r"cost", r"balance", r"mrr", r"arpu", r"ltv", r"fee",
    ]

    def detect_chart_type(
        self,
        data: List[Dict[str, Any]],
        columns: List[str],
        llm_suggestion: Optional[str] = None,
    ) -> ChartConfig:
        """
        Detect the best chart type for the given data.

        Args:
            data: Query results as list of dicts
            columns: Column names
            llm_suggestion: Optional suggestion from LLM

        Returns:
            ChartConfig with visualization settings
        """
        if not data or not columns:
            return ChartConfig(type="table", title="No data")

        # Single value -> Big Number
        if len(data) == 1 and len(columns) == 1:
            col = columns[0]
            value = data[0][col]
            if isinstance(value, (int, float)):
                return ChartConfig(
                    type="number",
                    title=self._format_title(col),
                    format={"value": self._detect_format(col)},
                )

        # Single row with few columns -> Big Number (show first numeric)
        if len(data) == 1 and len(columns) <= 3:
            for col in columns:
                if isinstance(data[0][col], (int, float)):
                    return ChartConfig(
                        type="number",
                        title=self._format_title(col),
                        y_axis=col,
                        format={"value": self._detect_format(col)},
                    )

        # Detect column types
        date_cols = [c for c in columns if self._is_date_column(c, data)]
        numeric_cols = [c for c in columns if self._is_numeric_column(c, data)]
        categorical_cols = [c for c in columns if self._is_categorical_column(c, data)]

        # Time series -> Line Chart
        if date_cols and numeric_cols and len(data) > 1:
            return ChartConfig(
                type="line",
                title=self._format_title(numeric_cols[0]) + " over time",
                x_axis=date_cols[0],
                y_axis=numeric_cols[0] if len(numeric_cols) == 1 else numeric_cols,
                format={col: self._detect_format(col) for col in numeric_cols},
            )

        # Categorical + numeric with few categories -> Bar or Pie
        if categorical_cols and numeric_cols:
            unique_categories = len(set(row[categorical_cols[0]] for row in data))

            # Few categories that might sum to 100% -> Pie
            if unique_categories <= 6 and len(numeric_cols) == 1:
                total = sum(row[numeric_cols[0]] or 0 for row in data)
                if total > 0:
                    # Check if values are percentages or could represent parts of a whole
                    return ChartConfig(
                        type="pie",
                        title=f"{self._format_title(numeric_cols[0])} by {self._format_title(categorical_cols[0])}",
                        x_axis=categorical_cols[0],  # Labels
                        y_axis=numeric_cols[0],  # Values
                        format={numeric_cols[0]: self._detect_format(numeric_cols[0])},
                    )

            # Categorical comparison -> Bar Chart
            if unique_categories <= 20:
                return ChartConfig(
                    type="bar",
                    title=f"{self._format_title(numeric_cols[0])} by {self._format_title(categorical_cols[0])}",
                    x_axis=categorical_cols[0],
                    y_axis=numeric_cols[0],
                    format={numeric_cols[0]: self._detect_format(numeric_cols[0])},
                )

        # Use LLM suggestion if provided and makes sense
        if llm_suggestion and llm_suggestion in ["line", "bar", "pie", "number"]:
            if llm_suggestion == "line" and date_cols and numeric_cols:
                return ChartConfig(
                    type="line",
                    x_axis=date_cols[0],
                    y_axis=numeric_cols[0] if len(numeric_cols) == 1 else numeric_cols,
                )
            elif llm_suggestion == "bar" and categorical_cols and numeric_cols:
                return ChartConfig(
                    type="bar",
                    x_axis=categorical_cols[0],
                    y_axis=numeric_cols[0],
                )
            elif llm_suggestion == "pie" and categorical_cols and numeric_cols:
                return ChartConfig(
                    type="pie",
                    x_axis=categorical_cols[0],
                    y_axis=numeric_cols[0],
                )
            elif llm_suggestion == "number" and numeric_cols and len(data) == 1:
                return ChartConfig(
                    type="number",
                    y_axis=numeric_cols[0],
                )

        # Default to table
        return ChartConfig(
            type="table",
            title="Query Results",
            format={col: self._detect_format(col) for col in columns},
        )

    def _is_date_column(self, col: str, data: List[Dict[str, Any]]) -> bool:
        """Check if a column contains date/time values."""
        col_lower = col.lower()

        # Check name patterns
        for pattern in self.DATE_PATTERNS:
            if re.search(pattern, col_lower):
                return True

        # Check actual values
        if data:
            value = data[0].get(col)
            if isinstance(value, str):
                # Check for ISO date format
                if re.match(r"\d{4}-\d{2}-\d{2}", value):
                    return True

        return False

    def _is_numeric_column(self, col: str, data: List[Dict[str, Any]]) -> bool:
        """Check if a column contains numeric values."""
        if not data:
            return False

        # Check actual values
        value = data[0].get(col)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return True

        # Check name patterns
        col_lower = col.lower()
        for pattern in self.NUMERIC_PATTERNS:
            if re.search(pattern, col_lower):
                return True

        return False

    def _is_categorical_column(self, col: str, data: List[Dict[str, Any]]) -> bool:
        """Check if a column contains categorical values."""
        if not data:
            return False

        # Check if it's a string column with limited unique values
        value = data[0].get(col)
        if isinstance(value, str):
            unique_values = len(set(row.get(col) for row in data))
            if unique_values <= 50:  # Reasonable number of categories
                return True

        # Check name patterns
        col_lower = col.lower()
        for pattern in self.CATEGORICAL_PATTERNS:
            if re.search(pattern, col_lower):
                return True

        return False

    def _detect_format(self, col: str) -> str:
        """Detect the display format for a column."""
        col_lower = col.lower()

        # Currency
        for pattern in self.CURRENCY_PATTERNS:
            if re.search(pattern, col_lower):
                return "currency"

        # Percentage
        if re.search(r"percent|rate|ratio", col_lower):
            return "percent"

        # Date
        for pattern in self.DATE_PATTERNS:
            if re.search(pattern, col_lower):
                return "date"

        # Count/integer
        if re.search(r"count|number|qty|quantity", col_lower):
            return "integer"

        return "number"

    def _format_title(self, col: str) -> str:
        """Format a column name as a title."""
        # Replace underscores and camelCase
        title = re.sub(r"_", " ", col)
        title = re.sub(r"([a-z])([A-Z])", r"\1 \2", title)
        return title.title()


def get_auto_visualizer() -> AutoVisualizer:
    """Factory function for AutoVisualizer."""
    return AutoVisualizer()
