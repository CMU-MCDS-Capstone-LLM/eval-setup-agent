"""Command-line interface for env_setup_agent."""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Optional

from .core.models import RepoSpec
from .runflow import run_one
from .config import load_from_env
from .adapters.github_commit import python_version_cap_from_date
from .io.repo_index import list_repos, find_processed_repos


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="env-setup-agent",
        description="Generate Docker environments for Python repositories"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # scan command
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan repository and gather facts"
    )
    scan_parser.add_argument("repo_path", type=Path, help="Path to repository")

    # generate command
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate Docker environment for a repository"
    )
    generate_parser.add_argument("env_id", help="Environment ID")
    generate_parser.add_argument("repo_name", help="Repository name (org/repo)")
    generate_parser.add_argument("commit_sha", help="Commit SHA")
    generate_parser.add_argument("commit_date", help="Commit date (ISO format)")
    generate_parser.add_argument("--data-root", type=Path, default=Path("data"), help="Data root directory")
    generate_parser.add_argument("--model", help="Claude model name")
    generate_parser.add_argument("--max-rounds", type=int, default=3, help="Maximum iteration rounds")

    # list command
    list_parser = subparsers.add_parser(
        "list",
        help="List repositories and their status"
    )
    list_parser.add_argument("--data-root", type=Path, default=Path("data"), help="Data root directory")

    # all command (batch process)
    all_parser = subparsers.add_parser(
        "all",
        help="Process all repositories in data/repos"
    )
    all_parser.add_argument("--data-root", type=Path, default=Path("data"), help="Data root directory")
    all_parser.add_argument("--model", help="Claude model name")
    all_parser.add_argument("--max-rounds", type=int, default=3, help="Maximum iteration rounds")
    all_parser.add_argument("--skip-existing", action="store_true", help="Skip already processed repos")

    return parser


async def cmd_scan(args: argparse.Namespace) -> int:
    """Execute scan command."""
    from .detect.facts import gather_facts

    repo_path = args.repo_path.resolve()
    if not repo_path.exists():
        print(f"Error: Repository not found: {repo_path}", file=sys.stderr)
        return 1

    print(f"Scanning repository: {repo_path}")
    facts = gather_facts(repo_path)

    print("\nFacts discovered:")
    print(f"  Tests found: {len(facts.tests_found)}")
    print(f"  Python constraints: {facts.python_constraints}")
    print(f"  Python cap: {facts.python_cap_minor[0]}.{facts.python_cap_minor[1]}")
    print(f"  Dependency manifests: {facts.dep_manifests}")
    print(f"  System packages: {facts.sys_packages}")
    print(f"  Service indicators: {len(facts.service_indicators)}")
    print(f"  Test subdir: {facts.test_subdir}")
    print(f"  Allow editable: {facts.allow_editable}")

    return 0


async def cmd_generate(args: argparse.Namespace) -> int:
    """Execute generate command."""
    data_root = args.data_root.resolve()
    repo_path = data_root / "repos" / args.env_id
    env_dir = data_root / "envs" / args.env_id

    if not repo_path.exists():
        print(f"Error: Repository not found: {repo_path}", file=sys.stderr)
        return 1

    # Create spec
    spec = RepoSpec(
        env_id=args.env_id,
        repo_name=args.repo_name,
        commit_sha=args.commit_sha,
        commit_ts_iso=args.commit_date,
        repo_path=str(repo_path),
        env_dir=str(env_dir)
    )

    # Determine Python cap from commit date
    python_cap = python_version_cap_from_date(args.commit_date)

    # Load config
    config = load_from_env()
    model = args.model or config.agent.model
    max_rounds = args.max_rounds

    # Paths
    prompts_dir = Path(config.paths.prompts_dir)
    templates_dir = Path(config.paths.templates_dir)

    print(f"Generating environment for: {args.repo_name} @ {args.commit_sha}")
    print(f"Python cap: {python_cap[0]}.{python_cap[1]}")
    print(f"Model: {model or 'default'}")
    print(f"Max rounds: {max_rounds}")
    print()

    # Run generation
    decision = await run_one(
        spec=spec,
        python_cap_minor=python_cap,
        prompts_dir=prompts_dir,
        templates_dir=templates_dir,
        data_root=data_root,
        model=model,
        max_rounds=max_rounds
    )

    # Report result
    if decision.status.value == "proceed":
        print(f"\n✓ SUCCESS: Environment generated at {env_dir}")
        print(f"  Dockerfile: {env_dir / 'Dockerfile'}")
        print(f"  Run script: {env_dir / 'run_instructions.sh'}")
    else:
        print(f"\n✗ REFUSED: {decision.reason}")
        print(f"  See: {env_dir / 'summary.md'}")

    return 0 if decision.status.value == "proceed" else 1


async def cmd_list(args: argparse.Namespace) -> int:
    """Execute list command."""
    data_root = args.data_root.resolve()

    all_repos = list_repos(data_root)
    success_ids, failure_ids = find_processed_repos(data_root)

    print(f"Total repositories: {len(all_repos)}")
    print(f"Successful: {len(success_ids)}")
    print(f"Failed: {len(failure_ids)}")
    print(f"Pending: {len(all_repos) - len(success_ids) - len(failure_ids)}")
    print()

    if success_ids:
        print("Successful:")
        for env_id in sorted(success_ids):
            print(f"  ✓ {env_id}")
        print()

    if failure_ids:
        print("Failed:")
        for env_id in sorted(failure_ids):
            print(f"  ✗ {env_id}")
        print()

    pending = set(all_repos) - set(success_ids) - set(failure_ids)
    if pending:
        print("Pending:")
        for env_id in sorted(pending):
            print(f"  - {env_id}")

    return 0


async def cmd_all(args: argparse.Namespace) -> int:
    """Execute all command (batch processing)."""
    data_root = args.data_root.resolve()
    all_repos = list_repos(data_root)

    if args.skip_existing:
        success_ids, failure_ids = find_processed_repos(data_root)
        processed = set(success_ids) | set(failure_ids)
        all_repos = [r for r in all_repos if r not in processed]

    if not all_repos:
        print("No repositories to process.")
        return 0

    print(f"Processing {len(all_repos)} repositories...")
    print()

    # Load config
    config = load_from_env()
    model = args.model or config.agent.model
    max_rounds = args.max_rounds
    prompts_dir = Path(config.paths.prompts_dir)
    templates_dir = Path(config.paths.templates_dir)

    success_count = 0
    failure_count = 0

    for i, env_id in enumerate(all_repos, 1):
        print(f"[{i}/{len(all_repos)}] Processing: {env_id}")

        repo_path = data_root / "repos" / env_id
        env_dir = data_root / "envs" / env_id

        # We need repo metadata - this is a simplified version
        # In practice, you'd load this from a metadata file
        spec = RepoSpec(
            env_id=env_id,
            repo_name=env_id.replace("__", "/", 1),
            commit_sha="unknown",
            commit_ts_iso="2024-01-01T00:00:00Z",
            repo_path=str(repo_path),
            env_dir=str(env_dir)
        )

        python_cap = (3, 11)  # Default

        try:
            decision = await run_one(
                spec=spec,
                python_cap_minor=python_cap,
                prompts_dir=prompts_dir,
                templates_dir=templates_dir,
                data_root=data_root,
                model=model,
                max_rounds=max_rounds
            )

            if decision.status.value == "proceed":
                print(f"  ✓ Success")
                success_count += 1
            else:
                print(f"  ✗ Refused: {decision.reason}")
                failure_count += 1

        except Exception as e:
            print(f"  ✗ Error: {e}")
            failure_count += 1

        print()

    print(f"Completed: {success_count} successful, {failure_count} failed")
    return 0


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Dispatch to command handlers
    if args.command == "scan":
        return asyncio.run(cmd_scan(args))
    elif args.command == "generate":
        return asyncio.run(cmd_generate(args))
    elif args.command == "list":
        return asyncio.run(cmd_list(args))
    elif args.command == "all":
        return asyncio.run(cmd_all(args))
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
