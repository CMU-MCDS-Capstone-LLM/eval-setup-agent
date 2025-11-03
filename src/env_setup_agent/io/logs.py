"""Simple JSONL logging."""

import json
from pathlib import Path
from typing import Any, Dict
from datetime import datetime


def append_log(log_path: Path, event: Dict[str, Any]) -> None:
    """
    Append a log event to a JSONL file.

    Args:
        log_path: Path to log file
        event: Event dictionary to log
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Add timestamp if not present
    if "timestamp" not in event:
        event["timestamp"] = datetime.utcnow().isoformat() + "Z"

    with log_path.open("a") as f:
        f.write(json.dumps(event) + "\n")


def read_logs(log_path: Path) -> list:
    """
    Read all log events from a JSONL file.

    Args:
        log_path: Path to log file

    Returns:
        List of event dictionaries
    """
    if not log_path.exists():
        return []

    events = []
    with log_path.open("r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    return events
