"""Configuration loading and merging."""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from .model import Config, AgentConfig, PathConfig


def load_from_yaml(config_path: Path, repo_root: Optional[Path] = None) -> Config:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to YAML config file
        repo_root: Optional repository root for resolving relative paths

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

    # Determine repo root for resolving relative paths
    if repo_root is None:
        repo_root = config_path.parent

    # Parse agent config
    agent_data = data.get("agent", {})
    agent_config = AgentConfig(
        model=agent_data.get("model"),
        max_rounds=agent_data.get("max_rounds", 3),
        build_timeout_s=agent_data.get("build_timeout_s", 1800),
        run_timeout_s=agent_data.get("run_timeout_s", 1800),
    )

    # Parse path config
    paths_data = data.get("paths", {})

    # Resolve paths relative to repo_root if they're relative
    def resolve_path(path_str: str, default: str) -> str:
        if not path_str:
            path_str = default
        path = Path(path_str)
        if not path.is_absolute():
            path = repo_root / path
        return str(path.resolve())

    path_config = PathConfig(
        data_root=resolve_path(
            paths_data.get("data_root", ""),
            "data"
        ),
        prompts_dir=resolve_path(
            paths_data.get("prompts_dir", ""),
            "src/env_setup_agent/agent/prompts"
        ),
        templates_dir=resolve_path(
            paths_data.get("templates_dir", ""),
            "src/env_setup_agent/templating"
        ),
    )

    return Config(agent=agent_config, paths=path_config)


def load_from_env() -> Config:
    """
    Load configuration from environment variables.

    Environment variables:
        ESA_MODEL: Model name
        ESA_MAX_ROUNDS: Maximum iteration rounds
        ESA_BUILD_TIMEOUT: Build timeout in seconds
        ESA_RUN_TIMEOUT: Run timeout in seconds
        ESA_DATA_ROOT: Data root directory
        ESA_PROMPTS_DIR: Prompts directory
        ESA_TEMPLATES_DIR: Templates directory

    Returns:
        Config instance with values from environment
    """
    agent_config = AgentConfig(
        model=os.getenv("ESA_MODEL"),
        max_rounds=int(os.getenv("ESA_MAX_ROUNDS", "3")),
        build_timeout_s=int(os.getenv("ESA_BUILD_TIMEOUT", "1800")),
        run_timeout_s=int(os.getenv("ESA_RUN_TIMEOUT", "1800")),
    )

    path_config = PathConfig(
        data_root=os.getenv("ESA_DATA_ROOT", "data"),
        prompts_dir=os.getenv("ESA_PROMPTS_DIR", "src/env_setup_agent/agent/prompts"),
        templates_dir=os.getenv("ESA_TEMPLATES_DIR", "src/env_setup_agent/templating"),
    )

    return Config(agent=agent_config, paths=path_config)


def merge_configs(base: Config, **overrides: Any) -> Config:
    """
    Merge configuration overrides into base config.

    Args:
        base: Base configuration
        **overrides: Override values for agent or paths

    Returns:
        New Config instance with merged values
    """
    agent_overrides = overrides.get("agent", {})
    path_overrides = overrides.get("paths", {})

    agent_config = AgentConfig(
        model=agent_overrides.get("model", base.agent.model),
        max_rounds=agent_overrides.get("max_rounds", base.agent.max_rounds),
        build_timeout_s=agent_overrides.get("build_timeout_s", base.agent.build_timeout_s),
        run_timeout_s=agent_overrides.get("run_timeout_s", base.agent.run_timeout_s),
    )

    path_config = PathConfig(
        data_root=path_overrides.get("data_root", base.paths.data_root),
        prompts_dir=path_overrides.get("prompts_dir", base.paths.prompts_dir),
        templates_dir=path_overrides.get("templates_dir", base.paths.templates_dir),
    )

    return Config(agent=agent_config, paths=path_config)
