"""
Shared frequency-string → days conversion utility.

Single source of truth for all "Every N months / weekly / quarterly…" parsing.
Previously duplicated between preventive_logic.parse_frequency_string and
preventive_calculator.get_medicine_recurrence_days — now both import from here.
"""

import re


# Canonical mapping: named frequency keyword → days.
# Multiply-patterns (e.g. "Every 3 months") are resolved dynamically below.
_KEYWORD_DAYS: dict[str, int] = {
    "weekly":          7,
    "fortnightly":     14,
    "bi-weekly":       14,
    "biweekly":        14,
    "monthly":         30,
    "once a month":    30,
    "bi-monthly":      60,
    "bimonthly":       60,
    "quarterly":       90,
    "3 month":         90,
    "3-month":         90,
    "semi-annually":   180,
    "every 6 month":   180,
    "annually":        365,
    "yearly":          365,
    "once a year":     365,
}

# Days per unit for "Every N <unit>" patterns.
_UNIT_DAYS: dict[str, int] = {
    "day":   1,
    "week":  7,
    "month": 30,
    "year":  365,
}


def frequency_to_days(frequency_str: str | None) -> int | None:
    """
    Parse a frequency string into an equivalent number of days.

    Handles:
    - "Every N weeks / months / days / years"  → N × unit
    - Named keywords: "Monthly", "Quarterly", "Annually", etc.

    Args:
        frequency_str: Human-readable frequency label (case-insensitive).

    Returns:
        Number of days between occurrences, or None if unparseable.
    """
    if not frequency_str:
        return None

    freq = str(frequency_str).lower().strip()

    # "Every N <unit>[s]" pattern — handles weeks, months, days, years.
    match = re.search(r"every\s+(\d+)\s+(day|week|month|year)s?", freq)
    if match:
        n, unit = int(match.group(1)), match.group(2)
        return n * _UNIT_DAYS[unit]

    # Named keyword lookup — longest-match first to avoid "month" matching
    # inside "bi-monthly" before the full keyword is checked.
    for keyword, days in sorted(_KEYWORD_DAYS.items(), key=lambda kv: -len(kv[0])):
        if keyword in freq:
            return days

    return None


def days_to_frequency_label(days: int) -> str:
    """
    Return a human-readable label for a given number of days.

    Args:
        days: Number of days between occurrences.

    Returns:
        Display label, e.g. "Monthly", "Every 6 weeks".
    """
    _EXACT: dict[int, str] = {
        7:   "Weekly",
        14:  "Fortnightly",
        30:  "Monthly",
        60:  "Bi-monthly",
        90:  "Quarterly",
        180: "Semi-annually",
        365: "Annually",
    }
    if days in _EXACT:
        return _EXACT[days]
    if days % 7 == 0:
        return f"Every {days // 7} weeks"
    if days % 30 == 0:
        return f"Every {days // 30} months"
    return f"Every {days} days"
