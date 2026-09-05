"""Small conversions shared by the data and presentation layers."""

import re
from datetime import datetime


def parse_dt(value):
    """datetime or DATETIME text -> datetime; None for FOG's zero dates."""
    if isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def dt_text(value):
    dt = parse_dt(value)
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def seconds_since(value, now):
    dt = parse_dt(value)
    return int((now - dt).total_seconds()) if dt else None


def to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_mac(value):
    """Twelve lowercase hex digits, whatever separators the input used."""
    return re.sub(r"[^0-9a-f]", "", str(value or "").lower())


def pretty_mac(value):
    digits = normalize_mac(value)
    if len(digits) != 12:
        return value or None
    return ":".join(digits[i:i + 2] for i in range(0, 12, 2))
