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
    prompts_dir: str
    templates_dir: str


@dataclass
class EnvConfig:
    """Configuration for environment settings."""
    app_user: str
    mount_dir: str


@dataclass
class Config:
    """Main configuration."""
    agent: AgentConfig = field(default_factory=AgentConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    env: EnvConfig = field(default_factory=EnvConfig)
