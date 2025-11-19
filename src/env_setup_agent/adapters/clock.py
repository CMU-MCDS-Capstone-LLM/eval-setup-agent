"""Clock utilities for timestamps."""

from datetime import datetime


def utc_now_iso() -> str:
    """
    Get current UTC time in ISO format.

    Returns:
        ISO timestamp string with 'Z' suffix
    """
    return datetime.utcnow().isoformat() + "Z"


def parse_iso_timestamp(ts: str) -> datetime:
    """
    Parse ISO timestamp string.

    Args:
        ts: ISO timestamp string

    Returns:
        datetime object
    """
    # Handle both with and without 'Z' suffix
    ts = ts.replace("Z", "+00:00")
    return datetime.fromisoformat(ts)
