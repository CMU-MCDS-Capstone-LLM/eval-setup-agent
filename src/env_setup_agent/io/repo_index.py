"""Repository index utilities."""

from pathlib import Path
from typing import List, Tuple


def list_repos(data_root: Path) -> List[str]:
    """
    List all repository environment IDs.

    Args:
        data_root: Root data directory

    Returns:
        List of environment IDs
    """
    repos_dir = data_root / "repos"
    if not repos_dir.exists():
        return []

    return [d.name for d in repos_dir.iterdir() if d.is_dir()]


def find_processed_repos(data_root: Path) -> Tuple[List[str], List[str]]:
    """
    Find repos that have been processed (success or failure).

    Args:
        data_root: Root data directory

    Returns:
        Tuple of (success_ids, failure_ids)
    """
    envs_dir = data_root / "envs"
    if not envs_dir.exists():
        return [], []

    success_ids = []
    failure_ids = []

    for env_dir in envs_dir.iterdir():
        if not env_dir.is_dir():
            continue

        if (env_dir / "_SUCCESS").exists():
            success_ids.append(env_dir.name)
        elif (env_dir / "_FAILURE").exists():
            failure_ids.append(env_dir.name)

    return success_ids, failure_ids
