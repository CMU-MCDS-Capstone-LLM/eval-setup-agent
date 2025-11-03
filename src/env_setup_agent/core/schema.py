"""JSON schema validation for agent output."""

import json
from typing import Optional, Dict, Any
from jsonschema import Draft202012Validator

SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["status"],
    "properties": {
        "status": {"enum": ["proceed", "refuse"]},
        "reason": {"type": "string"},
        "evidence": {
            "type": "object",
            "additionalProperties": {"type": "array", "items": {"type": "string"}}
        },
        "variables": {
            "type": "object",
            "required": [
                "python_version_tag", "mount_dir", "repo_bind_src", "test_workdir",
                "app_user", "project_apt_packages", "env_vars", "pip_deps",
                "install_editable", "test_cmd"
            ],
            "properties": {
                "python_version_tag": {"type": "string", "pattern": r"^\d+\.\d+\.\d+-slim$"},
                "mount_dir": {"type": "string"},
                "repo_bind_src": {"type": "string"},
                "test_workdir": {"type": "string"},
                "app_user": {"type": "string"},
                "project_apt_packages": {"type": "array", "items": {"type": "string"}},
                "env_vars": {"type": "object", "additionalProperties": {"type": "string"}},
                "pip_deps": {"type": "array", "items": {"type": "string"}},
                "install_editable": {"type": "boolean"},
                "test_cmd": {"type": "array", "items": {"type": "string"}}
            },
            "additionalProperties": False
        }
    },
    "allOf": [
        {
            "if": {"properties": {"status": {"const": "proceed"}}},
            "then": {"required": ["variables"]}
        },
        {
            "if": {"properties": {"status": {"const": "refuse"}}},
            "then": {"required": ["reason"]}
        }
    ],
    "additionalProperties": False
}

VALIDATOR = Draft202012Validator(SCHEMA)


def validate_or_error(obj: dict) -> Optional[str]:
    """
    Validate a dict against the schema.

    Args:
        obj: Dictionary to validate

    Returns:
        None if valid, error message string if invalid
    """
    errs = sorted(VALIDATOR.iter_errors(obj), key=lambda e: e.path)
    return None if not errs else "\n".join(f"- {e.message}" for e in errs)
