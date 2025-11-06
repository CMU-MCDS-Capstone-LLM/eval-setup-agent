"""Main controller for environment setup flow."""

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Tuple
from jinja2 import Template

from .core.models import RepoSpec, Decision, DockerVars
from .core.enums import Status
from .core.summarize import write_summary
from .templating.jinja_env import make_env
from .docker.build import docker_build
from .docker.run import docker_run
from .docker.classify import classify_run_returncode
from .docker.instructions import write_build_and_run_scripts
from .agent.claude_runner import ClaudeRepoAgent

logger = logging.getLogger("env_setup_agent")


def render_dockerfile(
    env_dir: Path,
    templates_dir: Path,
    vars_dict: dict
) -> None:
    """
    Render Dockerfile from template.

    Args:
        env_dir: Environment directory
        templates_dir: Templates directory
        vars_dict: Variables for template
    """
    env = make_env(templates_dir)
    tpl = env.get_template("dockerfile.template.j2")
    dockerfile = tpl.render(**vars_dict)

    out_path = env_dir / "Dockerfile"
    env_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(dockerfile)


async def run_one(
    spec: RepoSpec,
    python_cap_minor: Tuple[int, int],
    prompts_dir: Path,
    templates_dir: Path,
    data_root: Path,
    model: str | None = None,
    max_rounds: int = 3,
    build_timeout_s: int = 1800,
    run_timeout_s: int = 1800
) -> Decision:
    """
    Run environment setup for a single repository.

    Args:
        spec: Repository specification
        python_cap_minor: Python version cap (major, minor)
        prompts_dir: Directory containing prompt templates
        templates_dir: Directory containing Dockerfile template
        data_root: Root data directory
        model: Optional model name override
        max_rounds: Maximum iteration rounds
        build_timeout_s: Build timeout in seconds
        run_timeout_s: Run timeout in seconds

    Returns:
        Final Decision from agent
    """
    logger.info(f"Starting environment setup for {spec.repo_name} @ {spec.commit_sha}")
    logger.info(f"Environment ID: {spec.env_id}")
    logger.info(f"Python cap: {python_cap_minor[0]}.{python_cap_minor[1]}")
    logger.info(f"Max rounds: {max_rounds}")

    # Load prompt fragments
    system_md = prompts_dir / "system.md"
    policy_md = prompts_dir / "policy.md"
    contract_json_path = prompts_dir / "contract.json"
    repo_task_tpl_path = prompts_dir / "repo_task.md.j2"

    logger.debug(f"Loading prompts from {prompts_dir}")
    assert(system_md.exists(), "Can proceed without a provided system prompt.")
    assert(policy_md.exists(), "Can proceed without a provided policy prompt.")
    assert(contract_json_path.exists(), "Can proceed without a provided contract json.")
    assert(repo_task_tpl_path.exists(), "Can proceed without a provided repo task template prompt.")

    system_txt = system_md.read_text() 
    policy_txt = policy_md.read_text()
    contract = contract_json_path.read_text()
    task_tpl_content = repo_task_tpl_path.read_text()
    task_tpl = Template(task_tpl_content)
    repo_task = task_tpl.render(
        repo_name=spec.repo_name,
        commit_sha=spec.commit_sha,
        python_cap_minor=python_cap_minor
    )

    # Create agent
    logger.info("Initializing Claude agent")
    agent = ClaudeRepoAgent(repo_path=Path(spec.repo_path), model=model)

    # Track iteration number for saving artifacts
    iteration_counter = {"count": 0}

    # Define build and test callback
    async def build_and_test_cb(dvars: DockerVars) -> Tuple[bool, str, str, str]:
        """
        Build and test callback.

        Args:
            dvars: Docker variables

        Returns:
            Tuple of (ok, build_tail, run_tail, classification)
        """
        iteration_counter["count"] += 1
        iteration_num = iteration_counter["count"]

        logger.info(f"=== Iteration {iteration_num} ===")

        # Create iteration directory
        iteration_dir = Path(spec.env_dir) / "iterations" / f"round_{iteration_num}"
        iteration_dir.mkdir(parents=True, exist_ok=True)

        # Save the decision JSON for this iteration
        decision_data = asdict(dvars)
        decision_json_path = iteration_dir / "decision.json"
        decision_json_path.write_text(json.dumps(decision_data, indent=2))
        logger.debug(f"Saved decision JSON to {decision_json_path}")

        # Render Dockerfile
        logger.info("Rendering Dockerfile from template")
        render_dockerfile(Path(spec.env_dir), templates_dir, asdict(dvars))

        # Also save Dockerfile to iteration directory
        dockerfile_content = (Path(spec.env_dir) / "Dockerfile").read_text()
        (iteration_dir / "Dockerfile").write_text(dockerfile_content)
        logger.debug(f"Saved Dockerfile to {iteration_dir}")

        # Build
        tag = f"envsetup/{spec.env_id}:tests"
        logger.info(f"Building Docker image: {tag}")
        bres = docker_build(
            Path(spec.env_dir),
            tag,
            data_root,
            timeout_s=build_timeout_s
        )

        build_tail = ""
        if Path(bres.log_path).exists():
            build_tail = Path(bres.log_path).read_text()[-32000:]

        if not bres.success:
            logger.error(f"Docker build failed: {bres.message}")
            logger.debug(f"Build log tail: {build_tail[-500:]}")

            # Save iteration result
            result_data = {
                "iteration": iteration_num,
                "success": False,
                "build_success": False,
                "classification": "build_failed",
                "message": bres.message
            }
            (iteration_dir / "result.json").write_text(json.dumps(result_data, indent=2))

            return (False, build_tail, "", "build_failed")

        logger.info("Docker build successful")

        # Run
        logger.info("Running tests in container")
        rc, run_log_path, status = docker_run(
            tag,
            Path(spec.repo_path),
            dvars.mount_dir,
            Path(spec.env_dir),
            timeout_s=run_timeout_s
        )

        run_tail = ""
        if Path(run_log_path).exists():
            run_tail = Path(run_log_path).read_text()[-32000:]

        cls = classify_run_returncode(rc, run_tail)
        ok = cls in ("ok", "pytest_failed")

        logger.info(f"Test run completed: rc={rc}, classification={cls}")
        if not ok:
            logger.debug(f"Run log tail: {run_tail[-500:]}")

        # Save iteration result
        result_data = {
            "iteration": iteration_num,
            "success": ok,
            "build_success": True,
            "test_returncode": rc,
            "classification": cls,
            "message": f"Classification: {cls}"
        }
        (iteration_dir / "result.json").write_text(json.dumps(result_data, indent=2))

        return (ok, build_tail, run_tail, cls)

    # Run agent
    logger.info("Starting agent iteration loop")
    decision = await agent.run(
        repo_name=spec.repo_name,
        commit_sha=spec.commit_sha,
        py_cap_minor=python_cap_minor,
        build_and_test_cb=build_and_test_cb,
        system_txt=system_txt,
        task_tpl=repo_task,
        policy_txt=policy_txt,
        contract_json=contract,
        max_rounds=max_rounds,
    )

    logger.info(f"Agent completed with status: {decision.status.value}")
    if iteration_counter["count"] > 0:
        logger.info(f"Completed {iteration_counter['count']} iteration(s)")

    # Write artifacts
    logger.info("Writing output artifacts")
    env_dir = Path(spec.env_dir)
    env_dir.mkdir(parents=True, exist_ok=True)

    # Write success/failure marker
    if decision.status is Status.PROCEED:
        logger.info("✓ Generation successful")
        (env_dir / "_SUCCESS").write_text("")
    else:
        logger.warning(f"✗ Generation refused: {decision.reason}")
        (env_dir / "_FAILURE").write_text("")

    # Write run instructions
    mount_dir = decision.variables.mount_dir if decision.variables else "/workspace"
    write_build_and_run_scripts(
        env_dir,
        f"envsetup/{spec.env_id}:tests",
        data_root,
        mount_dir,
        spec.env_id
    )
    logger.debug(f"Wrote build.sh and run.sh to {env_dir}")

    # Write summary
    write_summary(env_dir, spec, decision)
    logger.debug(f"Wrote summary.md to {env_dir}")

    # Write final decision JSON (at root level)
    decision_json = env_dir / "decision.json"
    decision_data = {
        "status": decision.status.value,
        "reason": decision.reason,
        "evidence": decision.evidence,
        "variables": asdict(decision.variables) if decision.variables else None
    }
    decision_json.write_text(json.dumps(decision_data, indent=2))
    logger.debug(f"Wrote decision.json to {env_dir}")

    logger.info(f"Environment setup complete for {spec.env_id}")
    if iteration_counter["count"] > 0:
        logger.info(f"Iteration artifacts saved to: {env_dir / 'iterations'}")

    return decision
