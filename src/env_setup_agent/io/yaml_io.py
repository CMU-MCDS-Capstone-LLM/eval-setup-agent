"""YAML I/O utilities."""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional


def load_yaml(path: Path) -> Optional[Dict[str, Any]]:
    """
    Load YAML file.

    Args:
        path: Path to YAML file

    Returns:
        Parsed YAML as dict, or None if file doesn't exist
    """
    if not path.exists():
        return None

    try:
        with path.open("r") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def write_yaml(path: Path, data: Dict[str, Any]) -> None:
    """
    Write data to YAML file.

    Args:
        path: Destination path
        data: Data to write
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
