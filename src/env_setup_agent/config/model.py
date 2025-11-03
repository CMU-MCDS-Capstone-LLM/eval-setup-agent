"""Configuration data models."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentConfig:
    """Configuration for the Claude agent."""
    model: Optional[str] = None
    max_rounds: int = 3
    build_timeout_s: int = 1800
    run_timeout_s: int = 1800


@dataclass
class PathConfig:
    """Configuration for paths."""
    data_root: str = "data"
    prompts_dir: str = "src/env_setup_agent/agent/prompts"
    templates_dir: str = "src/env_setup_agent/templating"


@dataclass
class Config:
    """Main configuration."""
    agent: AgentConfig = field(default_factory=AgentConfig)
    paths: PathConfig = field(default_factory=PathConfig)


# Default configuration
DEFAULT_CONFIG = Config()
