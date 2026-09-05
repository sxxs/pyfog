"""Small conversions shared by the data and presentation layers."""

import re
from datetime import datetime

# FOG writes zero dates into NOT NULL DATETIME columns to mean "never".
NULL_DATES = ("", "0000-00-00 00:00:00", "0000-00-00", "NULL", None)


def parse_dt(value):
    """MySQL DATETIME text -> datetime, or None for FOG's zero dates."""
    if isinstance(value, datetime):
        return value
    if value in NULL_DATES:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value)[:19], fmt)
        except ValueError:
            continue
    return None


def dt_text(value):
    """datetime or DATETIME text -> canonical text, None for never."""
    dt = parse_dt(value)
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def seconds_since(value, now):
    dt = parse_dt(value)
    if dt is None:
        return None
    return int((now - dt).total_seconds())


def to_int(value, default=0):
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def to_float(value, default=0.0):
    try:
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return default


def normalize_mac(value):
    """Twelve lowercase hex digits, whatever separators the input used."""
    if not value:
        return ""
    return re.sub(r"[^0-9a-f]", "", str(value).strip().lower())


def pretty_mac(value):
    digits = normalize_mac(value)
    if len(digits) != 12:
        return (value or "").strip().lower() or None
    return ":".join(digits[i:i + 2] for i in range(0, 12, 2))
