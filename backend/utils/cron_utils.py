"""
Cron utilities for schedule validation and next run calculation.

Provides functions for:
- Validating cron expressions
- Calculating next run times
- Parsing cron schedules with timezone support
"""

from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Optional, Dict, Any
import re

# Try to import zoneinfo (Python 3.9+), fall back to pytz for older versions
try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    USE_ZONEINFO = True
except ImportError:
    import pytz
    USE_ZONEINFO = False

    # Create compatibility layer for pytz
    class ZoneInfoNotFoundError(Exception):
        pass


class CronValidationError(Exception):
    """Raised when cron expression is invalid."""
    pass


class CronExpressionValidator:
    """
    Validates cron expressions.

    Supports standard 5-field cron format:
    - Minute (0-59)
    - Hour (0-23)
    - Day of month (1-31)
    - Month (1-12)
    - Day of week (0-6, 0=Sunday)

    Supports special characters:
    - * (any value)
    - , (value list separator)
    - - (range of values)
    - / (step values)
    """

    CRON_PATTERN = r'^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)$'

    FIELD_RANGES = {
        'minute': (0, 59),
        'hour': (0, 23),
        'day': (1, 31),
        'month': (1, 12),
        'weekday': (0, 6),
    }

    MONTH_NAMES = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }

    WEEKDAY_NAMES = {
        'sun': 0, 'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6
    }

    @classmethod
    def validate(cls, cron_expression: str) -> bool:
        """
        Validate a cron expression.

        Args:
            cron_expression: Cron expression string

        Returns:
            True if valid

        Raises:
            CronValidationError: If expression is invalid
        """
        if not cron_expression or not isinstance(cron_expression, str):
            raise CronValidationError("Cron expression must be a non-empty string")

        # Check pattern
        match = re.match(cls.CRON_PATTERN, cron_expression.strip())
        if not match:
            raise CronValidationError(
                "Invalid cron format. Expected: 'minute hour day month weekday'"
            )

        # Validate each field
        minute, hour, day, month, weekday = match.groups()

        try:
            cls._validate_field(minute, 'minute')
            cls._validate_field(hour, 'hour')
            cls._validate_field(day, 'day')
            cls._validate_field(month, 'month')
            cls._validate_field(weekday, 'weekday')
        except CronValidationError:
            raise

        return True

    @classmethod
    def _validate_field(cls, field: str, field_name: str) -> None:
        """Validate a single cron field."""
        min_val, max_val = cls.FIELD_RANGES[field_name]

        # Allow asterisk
        if field == '*':
            return

        # Handle comma-separated values
        for part in field.split(','):
            # Handle step values (e.g., */5, 0-23/2)
            if '/' in part:
                range_part, step = part.split('/', 1)
                try:
                    step_val = int(step)
                    if step_val <= 0:
                        raise CronValidationError(f"Step value must be positive in {field_name}")
                except ValueError:
                    raise CronValidationError(f"Invalid step value in {field_name}: {step}")

                if range_part != '*':
                    cls._validate_range(range_part, field_name, min_val, max_val)
            # Handle ranges (e.g., 1-5)
            elif '-' in part:
                cls._validate_range(part, field_name, min_val, max_val)
            # Handle single values
            else:
                cls._validate_single_value(part, field_name, min_val, max_val)

    @classmethod
    def _validate_range(cls, range_str: str, field_name: str, min_val: int, max_val: int) -> None:
        """Validate a range (e.g., 1-5)."""
        parts = range_str.split('-')
        if len(parts) != 2:
            raise CronValidationError(f"Invalid range in {field_name}: {range_str}")

        try:
            start = cls._parse_value(parts[0], field_name)
            end = cls._parse_value(parts[1], field_name)
        except ValueError as e:
            raise CronValidationError(f"Invalid range value in {field_name}: {str(e)}")

        if start < min_val or start > max_val:
            raise CronValidationError(
                f"Range start {start} out of bounds for {field_name} ({min_val}-{max_val})"
            )

        if end < min_val or end > max_val:
            raise CronValidationError(
                f"Range end {end} out of bounds for {field_name} ({min_val}-{max_val})"
            )

        if start > end:
            raise CronValidationError(
                f"Range start {start} must be <= range end {end} in {field_name}"
            )

    @classmethod
    def _validate_single_value(cls, value: str, field_name: str, min_val: int, max_val: int) -> None:
        """Validate a single value."""
        try:
            int_val = cls._parse_value(value, field_name)
        except ValueError as e:
            raise CronValidationError(f"Invalid value in {field_name}: {str(e)}")

        if int_val < min_val or int_val > max_val:
            raise CronValidationError(
                f"Value {int_val} out of bounds for {field_name} ({min_val}-{max_val})"
            )

    @classmethod
    def _parse_value(cls, value: str, field_name: str) -> int:
        """Parse a value (handles month/weekday names)."""
        value_lower = value.lower()

        # Handle month names
        if field_name == 'month' and value_lower in cls.MONTH_NAMES:
            return cls.MONTH_NAMES[value_lower]

        # Handle weekday names
        if field_name == 'weekday' and value_lower in cls.WEEKDAY_NAMES:
            return cls.WEEKDAY_NAMES[value_lower]

        try:
            return int(value)
        except ValueError:
            raise ValueError(f"Invalid value: {value}")


def validate_cron_expression(cron_expression: str) -> Dict[str, Any]:
    """
    Validate a cron expression and return details.

    Args:
        cron_expression: Cron expression string

    Returns:
        Dictionary with validation results and parsed fields

    Raises:
        CronValidationError: If expression is invalid
    """
    CronExpressionValidator.validate(cron_expression)

    parts = cron_expression.strip().split()
    return {
        'valid': True,
        'minute': parts[0],
        'hour': parts[1],
        'day': parts[2],
        'month': parts[3],
        'weekday': parts[4],
    }


def calculate_next_run(
    cron_expression: str,
    from_time: Optional[datetime] = None,
    timezone_str: str = 'UTC'
) -> datetime:
    """
    Calculate the next run time for a cron expression.

    Args:
        cron_expression: Cron expression string
        from_time: Calculate from this time (default: now)
        timezone_str: Timezone name (e.g., 'America/New_York', 'UTC')

    Returns:
        Next run time as datetime (UTC)

    Raises:
        CronValidationError: If expression is invalid
        ZoneInfoNotFoundError: If timezone is invalid
    """
    # Validate expression
    CronExpressionValidator.validate(cron_expression)

    # Get timezone
    try:
        if USE_ZONEINFO:
            tz = ZoneInfo(timezone_str)
        else:
            tz = pytz.timezone(timezone_str)
    except (ZoneInfoNotFoundError, pytz.exceptions.UnknownTimeZoneError):
        raise CronValidationError(f"Invalid timezone: {timezone_str}")

    # Get current time in the specified timezone
    if from_time is None:
        if USE_ZONEINFO:
            current_time = datetime.now(tz)
        else:
            current_time = datetime.now(pytz.utc).astimezone(tz)
    else:
        # Convert from_time to the specified timezone
        if from_time.tzinfo is None:
            # Assume UTC if no timezone
            if USE_ZONEINFO:
                current_time = from_time.replace(tzinfo=dt_timezone.utc).astimezone(tz)
            else:
                current_time = pytz.utc.localize(from_time).astimezone(tz)
        else:
            current_time = from_time.astimezone(tz)

    # Parse cron fields
    parts = cron_expression.strip().split()
    minute, hour, day, month, weekday = parts

    # Start from the next minute
    next_run = current_time.replace(second=0, microsecond=0) + timedelta(minutes=1)

    # Find next matching time (limit search to avoid infinite loops)
    max_iterations = 366 * 24 * 60  # One year worth of minutes
    iterations = 0

    while iterations < max_iterations:
        if (_matches_cron_field(next_run.minute, minute) and
            _matches_cron_field(next_run.hour, hour) and
            _matches_cron_field(next_run.day, day) and
            _matches_cron_field(next_run.month, month) and
            _matches_cron_field(next_run.weekday(), weekday)):
            # Convert to UTC before returning
            return next_run.astimezone(dt_timezone.utc)

        next_run += timedelta(minutes=1)
        iterations += 1

    raise CronValidationError("Could not find next run time (exceeded max iterations)")


def _matches_cron_field(value: int, pattern: str) -> bool:
    """
    Check if a value matches a cron field pattern.

    Args:
        value: The value to check
        pattern: The cron pattern (e.g., "*", "5", "1-5", "*/10")

    Returns:
        True if value matches pattern
    """
    # Asterisk matches everything
    if pattern == '*':
        return True

    # Handle comma-separated values
    for part in pattern.split(','):
        # Handle step values
        if '/' in part:
            range_part, step = part.split('/', 1)
            step_val = int(step)

            if range_part == '*':
                if value % step_val == 0:
                    return True
            else:
                # Handle range with step (e.g., 0-20/5)
                if '-' in range_part:
                    start, end = map(int, range_part.split('-'))
                    if start <= value <= end and (value - start) % step_val == 0:
                        return True

        # Handle ranges
        elif '-' in part:
            start, end = map(int, part.split('-'))
            if start <= value <= end:
                return True

        # Handle single values
        else:
            if value == int(part):
                return True

    return False


def get_cron_description(cron_expression: str) -> str:
    """
    Get a human-readable description of a cron expression.

    Args:
        cron_expression: Cron expression string

    Returns:
        Human-readable description
    """
    try:
        parts = cron_expression.strip().split()
        minute, hour, day, month, weekday = parts

        # Common patterns
        if cron_expression == '0 0 * * *':
            return "Daily at midnight (00:00)"
        elif cron_expression == '0 * * * *':
            return "Every hour"
        elif cron_expression == '*/5 * * * *':
            return "Every 5 minutes"
        elif cron_expression == '*/15 * * * *':
            return "Every 15 minutes"
        elif cron_expression == '*/30 * * * *':
            return "Every 30 minutes"
        elif cron_expression == '0 0 * * 0':
            return "Weekly on Sunday at midnight"
        elif cron_expression == '0 0 1 * *':
            return "Monthly on the 1st at midnight"

        # Build description
        desc_parts = []

        # Minutes
        if minute == '*':
            desc_parts.append("every minute")
        elif minute.startswith('*/'):
            step = minute.split('/')[1]
            desc_parts.append(f"every {step} minutes")
        else:
            desc_parts.append(f"at minute {minute}")

        # Hours
        if hour != '*':
            if '-' in hour:
                start, end = hour.split('-')
                desc_parts.append(f"between hours {start}-{end}")
            else:
                desc_parts.append(f"at hour {hour}")

        # Days
        if day != '*':
            desc_parts.append(f"on day {day}")

        # Months
        if month != '*':
            desc_parts.append(f"in month {month}")

        # Weekdays
        if weekday != '*':
            weekday_map = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
            if '-' in weekday:
                start, end = weekday.split('-')
                desc_parts.append(f"on {weekday_map[int(start)]}-{weekday_map[int(end)]}")
            else:
                desc_parts.append(f"on {weekday_map[int(weekday)]}")

        return " ".join(desc_parts).capitalize()

    except Exception:
        return cron_expression


# Predefined schedules
PREDEFINED_SCHEDULES = {
    'every_5_minutes': {
        'expression': '*/5 * * * *',
        'description': 'Every 5 minutes',
    },
    'every_15_minutes': {
        'expression': '*/15 * * * *',
        'description': 'Every 15 minutes',
    },
    'every_30_minutes': {
        'expression': '*/30 * * * *',
        'description': 'Every 30 minutes',
    },
    'hourly': {
        'expression': '0 * * * *',
        'description': 'Every hour',
    },
    'daily_midnight': {
        'expression': '0 0 * * *',
        'description': 'Daily at midnight (00:00)',
    },
    'daily_6am': {
        'expression': '0 6 * * *',
        'description': 'Daily at 6:00 AM',
    },
    'daily_noon': {
        'expression': '0 12 * * *',
        'description': 'Daily at noon (12:00)',
    },
    'daily_6pm': {
        'expression': '0 18 * * *',
        'description': 'Daily at 6:00 PM',
    },
    'weekly_sunday': {
        'expression': '0 0 * * 0',
        'description': 'Weekly on Sunday at midnight',
    },
    'weekly_monday': {
        'expression': '0 0 * * 1',
        'description': 'Weekly on Monday at midnight',
    },
    'monthly': {
        'expression': '0 0 1 * *',
        'description': 'Monthly on the 1st at midnight',
    },
}
