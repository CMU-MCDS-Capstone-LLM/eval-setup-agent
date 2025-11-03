"""Run env_setup_agent from YAML configuration file."""

import asyncio
import argparse
import sys
import yaml
from pathlib import Path
from typing import Optional

from .core.models import RepoSpec
from .config import load_from_yaml
from .runflow import run_one
from .adapters.github_commit import python_version_cap_from_date
from .utils.logging import setup_logging


def load_repo_spec(config_path: Path, repo_root: Path) -> RepoSpec:
    """
    Load repository specification from YAML config.

    Args:
        config_path: Path to YAML config file
        repo_root: Repository root directory

    Returns:
        RepoSpec instance

    Raises:
        ValueError: If required fields are missing
    """
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)

    repo_data = data.get("repository", {})

    # Extract required fields
    env_id = repo_data.get("env_id")
    repo_name = repo_data.get("repo_name")
    commit_sha = repo_data.get("commit_sha")
    commit_date = repo_data.get("commit_date")

    if not all([env_id, repo_name, commit_sha, commit_date]):
        raise ValueError(
            "Config must include repository.env_id, repository.repo_name, "
            "repository.commit_sha, and repository.commit_date"
        )

    # Resolve paths - repo_path and env_dir can be relative or absolute
    repo_path_str = repo_data.get("repo_path", "")
    env_dir_str = repo_data.get("env_dir", "")

    if repo_path_str:
        repo_path = Path(repo_path_str)
        if not repo_path.is_absolute():
            repo_path = repo_root / repo_path
    else:
        # Default: look for repos/<env_id> relative to repo_root
        repo_path = repo_root / "repos" / env_id

    if env_dir_str:
        env_dir = Path(env_dir_str)
        if not env_dir.is_absolute():
            env_dir = repo_root / env_dir
    else:
        # Default: envs/<env_id> relative to repo_root
        env_dir = repo_root / "envs" / env_id

    return RepoSpec(
        env_id=env_id,
        repo_name=repo_name,
        commit_sha=commit_sha,
        commit_ts_iso=commit_date,
        repo_path=str(repo_path.resolve()),
        env_dir=str(env_dir.resolve())
    )


async def run_from_config(config_path: Path, repo_root: Optional[Path] = None) -> int:
    """
    Run environment setup from YAML config.

    Args:
        config_path: Path to YAML config file
        repo_root: Optional repository root for resolving relative paths.
                  Defaults to config file's parent directory.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    config_path = config_path.resolve()

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        return 1

    # Determine repo root
    if repo_root is None:
        # Default: find git root or use config directory
        current = config_path.parent
        while current != current.parent:
            if (current / ".git").exists():
                repo_root = current
                break
            current = current.parent
        if repo_root is None:
            repo_root = config_path.parent

    repo_root = repo_root.resolve()

    try:
        # Load configuration
        config = load_from_yaml(config_path, repo_root)
        spec = load_repo_spec(config_path, repo_root)

        # Setup logging
        env_dir = Path(spec.env_dir)
        log_file = env_dir / "agent.log"
        setup_logging(log_file=log_file, level=20)  # INFO level

        from .utils.logging import get_logger
        logger = get_logger()

        logger.info("=" * 80)
        logger.info(f"Running env_setup_agent from config: {config_path}")
        logger.info(f"Repository root: {repo_root}")
        logger.info("=" * 80)

        # Validate repo path exists
        repo_path = Path(spec.repo_path)
        if not repo_path.exists():
            logger.error(f"Repository path not found: {repo_path}")
            return 1

        # Determine Python version cap from commit date
        python_cap = python_version_cap_from_date(spec.commit_ts_iso)
        logger.info(f"Python version cap from commit date: {python_cap[0]}.{python_cap[1]}")

        # Get paths from config
        prompts_dir = Path(config.paths.prompts_dir)
        templates_dir = Path(config.paths.templates_dir)
        data_root = Path(config.paths.data_root)

        logger.info(f"Prompts directory: {prompts_dir}")
        logger.info(f"Templates directory: {templates_dir}")
        logger.info(f"Data root: {data_root}")

        # Run generation
        decision = await run_one(
            spec=spec,
            python_cap_minor=python_cap,
            prompts_dir=prompts_dir,
            templates_dir=templates_dir,
            data_root=data_root,
            model=config.agent.model,
            max_rounds=config.agent.max_rounds,
            build_timeout_s=config.agent.build_timeout_s,
            run_timeout_s=config.agent.run_timeout_s
        )

        # Log final result
        logger.info("=" * 80)
        if decision.status.value == "proceed":
            logger.info(f"✓ SUCCESS: Environment generated at {env_dir}")
            logger.info(f"  Dockerfile: {env_dir / 'Dockerfile'}")
            logger.info(f"  Run script: {env_dir / 'run_instructions.sh'}")
            logger.info(f"  Log file: {log_file}")
        else:
            logger.warning(f"✗ REFUSED: {decision.reason}")
            logger.info(f"  Summary: {env_dir / 'summary.md'}")
            logger.info(f"  Log file: {log_file}")
        logger.info("=" * 80)

        return 0 if decision.status.value == "proceed" else 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="env-setup-agent-from-config",
        description="Run env_setup_agent from YAML configuration"
    )
    parser.add_argument(
        "config",
        type=Path,
        help="Path to YAML config file (e.g., demo/new-example/configs/.../env-setup-agent-config.yaml)"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="Repository root directory (default: auto-detect from .git or use config directory)"
    )

    args = parser.parse_args()

    return asyncio.run(run_from_config(args.config, args.repo_root))


if __name__ == "__main__":
    sys.exit(main())
