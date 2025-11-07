"""Configuration loading and merging."""

import yaml
from pathlib import Path

from .model import Config, AgentConfig, PathConfig, EnvConfig


def load_from_yaml(config_path: Path) -> Config:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to YAML config file

    Returns:
        Config instance with values from YAML

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config format is invalid
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("Config must be a YAML dictionary")

    agent_data = data.get("agent", {})
    agent_config = AgentConfig.from_dict(agent_data)

    paths_data = data.get("paths", {})
    path_config = PathConfig.from_dict(paths_data)

    env_data = data.get("env", {})
    env_config = EnvConfig.from_dict(env_data)

    return Config(agent=agent_config, paths=path_config, env=env_config)
