"""Configuration data models."""

from dataclasses import dataclass
from typing import Optional, Self
from pathlib import Path

from .. import resources
from .. import consts


def resolve_path(path_str: str, default: str | Path, require_exists: bool = False) -> Path:
    """
    Resolve paths, or set as default
    """
    if not path_str:
        path_str = str(default)
    path = Path(path_str)
    if not path.is_absolute():
        raise RuntimeError(f"Path must be absolute. Instead, got {path_str}")
    if require_exists and not path.exists():
        raise RuntimeError(f"Path {path} must exists.")
    return path.resolve()


@dataclass
class AgentConfig:
    """Configuration for the Claude agent."""

    model: Optional[str] = None
    max_rounds: int = 3
    build_timeout_s: int = 1800
    run_timeout_s: int = 1800
    output_retries: int = 2
    # If there exists a successful run, should we overwrite it?
    overwrite_success: bool = False
    # If there exists a failed run, should we overwrite it?
    overwrite_failure: bool = False

    @classmethod
    def from_dict(cls, agent_data: dict) -> Self:
        return cls(
            model=agent_data.get("model", consts.DEFAULT_MODEL),
            max_rounds=agent_data.get("max_rounds", consts.DEFAULT_MAX_ROUNDS),
            build_timeout_s=agent_data.get("build_timeout_s", consts.DEFAULT_BUILD_TIMEOUT_S),
            run_timeout_s=agent_data.get("run_timeout_s", consts.DEFAULT_RUN_TIMEOUT_S),
            output_retries=agent_data.get("output_retries", consts.DEFAULT_OUTPUT_RETRIES),
            overwrite_success=agent_data.get("overwrite_success", False),
            overwrite_failure=agent_data.get("overwrite_failure", False),
        )


@dataclass
class PathConfig:
    """Configuration for paths."""

    # prompt-related
    contract_json_path: Path
    initial_tpl_path: Path
    iterate_tpl_path: Path
    policy_prompt_path: Path
    repo_task_tpl_path: Path
    system_prompt_path: Path

    # others
    dockerfile_tpl_path: Path
    build_script_tpl_path: Path
    run_script_tpl_path: Path

    @classmethod
    def from_dict(cls, paths_data: dict) -> Self:
        return cls(
            # prompt-related
            contract_json_path=resolve_path(
                paths_data.get("contract_json_path", ""),
                resources.get_default_contract_json_path(),
                require_exists=True,
            ),
            initial_tpl_path=resolve_path(
                paths_data.get("initial_tpl_path", ""), resources.get_default_initial_tpl_path(), require_exists=True
            ),
            iterate_tpl_path=resolve_path(
                paths_data.get("iterate_tpl_path", ""), resources.get_default_iterate_tpl_path(), require_exists=True
            ),
            policy_prompt_path=resolve_path(
                paths_data.get("policy_prompt_path", ""),
                resources.get_default_policy_prompt_path(),
                require_exists=True,
            ),
            repo_task_tpl_path=resolve_path(
                paths_data.get("repo_task_tpl_path", ""),
                resources.get_default_repo_task_tpl_path(),
                require_exists=True,
            ),
            system_prompt_path=resolve_path(
                paths_data.get("system_prompt_path", ""),
                resources.get_default_system_prompt_path(),
                require_exists=True,
            ),
            # others
            dockerfile_tpl_path=resolve_path(
                paths_data.get("dockerfile_tpl_path", ""),
                resources.get_default_dockerfile_tpl_path(),
                require_exists=True,
            ),
            build_script_tpl_path=resolve_path(
                paths_data.get("build_script_tpl_path", ""),
                resources.get_default_build_script_tpl_path(),
                require_exists=True,
            ),
            run_script_tpl_path=resolve_path(
                paths_data.get("run_script_tpl_path", ""),
                resources.get_default_run_script_tpl_path(),
                require_exists=True,
            ),
        )


@dataclass
class EnvConfig:
    """Configuration for environment settings."""

    app_user: str
    mount_dir: str

    @classmethod
    def from_dict(cls, env_data: dict) -> Self:
        return cls(
            app_user=env_data.get("app_user", consts.DEFAULT_APP_USER),
            mount_dir=env_data.get("mount_dir", consts.DEFAULT_MOUNT_DIR),
        )


@dataclass
class Config:
    """Main configuration."""

    agent: AgentConfig
    paths: PathConfig
    env: EnvConfig
