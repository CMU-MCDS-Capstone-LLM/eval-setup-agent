"""Path utilities for data directory structure."""

from pathlib import Path
from typing import Tuple


def get_data_paths(data_root: Path, env_id: str) -> Tuple[Path, Path, Path, Path]:
    """
    Get standard paths for an environment.

    Args:
        data_root: Root data directory
        env_id: Environment identifier

    Returns:
        Tuple of (repo_path, env_dir, trajectory_dir, prompt_dir)
    """
    repo_path = data_root / "repos" / env_id
    env_dir = data_root / "envs" / env_id
    trajectory_dir = data_root / "trajectories" / env_id
    prompt_dir = data_root / "prompts" / env_id

    return repo_path, env_dir, trajectory_dir, prompt_dir


def ensure_dirs(*paths: Path) -> None:
    """
    Ensure directories exist.

    Args:
        *paths: Paths to create
    """
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)
