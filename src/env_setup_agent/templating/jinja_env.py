"""Jinja2 environment setup."""

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pathlib import Path


def make_env(templates_dir: Path) -> Environment:
    """
    Create Jinja2 environment for templates.

    Args:
        templates_dir: Directory containing templates

    Returns:
        Configured Jinja2 Environment
    """
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
