"""Command-line interface for env_setup_agent."""

import asyncio
import argparse
import sys
import yaml
from pathlib import Path
from typing import Optional
import os
import logging

from .core.models import RepoSpec
from .config import load_from_yaml
from .runflow import run_one
from .adapters.github_commit import CommitInfoFetcher
from .utils.logging import setup_logging, get_logger


def load_repo_spec(config_path: Path) -> RepoSpec:
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

    repo_data = data["repository"]

    # Extract required fields
    env_id = repo_data["env_id"]
    repo_name = repo_data["repo_name"]
    commit_sha = repo_data["commit_sha"]

    repo_path = Path(repo_data["repo_path"])
    env_dir = Path(repo_data["env_dir"])

    assert repo_path.is_absolute(), "Repo path must be absolute path"
    assert env_dir.is_absolute(), "Env dir must be absolute path"

    return RepoSpec(
        env_id=env_id,
        repo_name=repo_name,
        commit_sha=commit_sha,
        repo_path=str(repo_path.resolve()),
        env_dir=str(env_dir.resolve())
    )


async def run_from_config(config_path: Path) -> int:
    """
    Run environment setup from YAML config.

    Args:
        config_path: Path to YAML config file

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    config_path = config_path.resolve()

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        # Load configuration
        config = load_from_yaml(config_path)
        repo_spec = load_repo_spec(config_path)

        # Setup logging
        env_dir = Path(repo_spec.env_dir)
        log_file = env_dir / "env_setup_agent.log"
        setup_logging(log_file=log_file, level=logging.DEBUG)

        logger = get_logger()

        logger.info(f"Running env_setup_agent from config: {config_path}")

        # Validate repo path exists
        repo_path = Path(repo_spec.repo_path)
        if not repo_path.exists():
            logger.error(f"Repository path not found: {repo_path}")
            return 1

        # Determine Python version cap from commit date
        # Python version cap is the maximal python major+minor version possible, based on the timestamp of migration commit
        commit_info_fetcher = CommitInfoFetcher(os.getenv("GITHUB_TOKEN"))
        python_cap = commit_info_fetcher.infer_python_upper_bound_for_repo(repo_spec.repo_name, repo_spec.commit_sha)
        logger.info(f"Python version cap for commit {repo_spec.repo_name} @ {repo_spec.commit_sha}: {python_cap[0]}.{python_cap[1]}")

        # Get paths from config
        prompts_dir = Path(config.paths.prompts_dir).resolve()
        templates_dir = Path(config.paths.templates_dir).resolve()

        logger.info(f"Prompts directory: {prompts_dir}")
        logger.info(f"Templates directory: {templates_dir}")

        # Run generation
        decision = await run_one(
            spec=repo_spec,
            python_cap_minor=python_cap,
            env_id=repo_spec.env_id,
            prompts_dir=prompts_dir,
            templates_dir=templates_dir,
            app_user=config.env.app_user,
            mount_dir=config.env.mount_dir,
            model=config.agent.model,
            max_rounds=config.agent.max_rounds,
            build_timeout_s=config.agent.build_timeout_s,
            run_timeout_s=config.agent.run_timeout_s
        )

        # Log final result
        if decision.status.value == "proceed":
            logger.info(f"✓ SUCCESS: Environment generated at {env_dir}")
            logger.info(f"  Dockerfile: {env_dir / 'Dockerfile'}")
            logger.info(f"  Build script: {env_dir / 'build.sh'}")
            logger.info(f"  Run script: {env_dir / 'run.sh'}")
            logger.info(f"  Log file: {log_file}")
        else:
            logger.warning(f"✗ REFUSED: {decision.reason}")
            logger.info(f"  Summary: {env_dir / 'summary.md'}")
            logger.info(f"  Log file: {log_file}")

        return 0 if decision.status.value == "proceed" else 1

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error: {e}")
        import traceback
        tb_str = traceback.format_exc()
        logger.error(tb_str)
        return 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="env-setup-agent",
        description="Generate Docker environment for a Python repository from YAML config"
    )
    parser.add_argument(
        "config",
        type=Path,
        help="Path to YAML config file"
    )

    args = parser.parse_args()

    return asyncio.run(run_from_config(args.config))


if __name__ == "__main__":
    sys.exit(main())
