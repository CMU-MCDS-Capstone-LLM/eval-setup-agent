"""Main controller for environment setup flow."""

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import List, Tuple
from pathlib import Path

from env_setup_agent.consts.docker import DEFAULT_DOCKER_BUILD_SCRIPT_FILENAME, DEFAULT_DOCKER_RUN_SCRIPT_FILENAME

from .consts import DECISION_JSON_FILENAME
from .config.model import AgentConfig, EnvConfig, PathConfig
from .docker import get_image_tag
from .core.models import RepoSpec, Decision, DockerVars
from .core.enums import DecisionStatus
from .core.summarize import write_summary
from .templating.jinja_env import make_env
from .templating.render import render_from_path, render_and_save
from .docker.build import docker_build
from .docker.run import docker_run
from .docker.classify import classify_run_returncode
from .agent.claude_runner import ClaudeRepoAgent

logger = logging.getLogger("env_setup_agent")


async def run_one(
    spec: RepoSpec,
    python_cap_minor: Tuple[int, int],
    env_id: str,
    path_config: PathConfig,
    env_config: EnvConfig,
    agent_config: AgentConfig,
) -> Decision:
    """
    Run environment setup for a single repository.

    Args:
        spec: Repository specification
        python_cap_minor: Python version cap (major, minor)
        path_config: Configs related to path
        app_user: App user name for Docker
        mount_dir: Mount directory path for Docker
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
    logger.info(f"Max rounds: {agent_config.max_rounds}")

    # Load prompt fragments
    system_prompt = path_config.system_prompt_path.read_text()
    policy_prompt = path_config.policy_prompt_path.read_text()
    contract = path_config.contract_json_path.read_text()
    repo_task = render_from_path(
        path_config.repo_task_tpl_path,
        {"repo_name": spec.repo_name, "commit_sha": spec.commit_sha, "python_cap_minor": python_cap_minor},
    )

    # Create agent
    logger.info("Initializing Claude agent")
    agent = ClaudeRepoAgent(repo_path=Path(spec.repo_path), model=agent_config.model)

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
        decision_json_path = iteration_dir / DECISION_JSON_FILENAME
        decision_json_path.write_text(json.dumps(decision_data, indent=2))
        logger.debug(f"Saved decision JSON to {decision_json_path}")

        # Define image tag for this iteration
        tag = get_image_tag(env_id)

        # Render Dockerfile
        logger.info("Rendering Dockerfile from template")
        # Merge config-provided and LLM-provided variables
        # Compute test_workdir from mount_dir + test_worksubdir
        dvars_dict = asdict(dvars)
        test_worksubdir = dvars_dict.pop("test_worksubdir")
        # test_workdir = os.path.join(mount_dir, test_worksubdir)
        test_workdir = str((Path(env_config.mount_dir) / test_worksubdir).resolve())

        template_vars = {
            "app_user": env_config.app_user,
            "mount_dir": env_config.mount_dir,
            "test_workdir": test_workdir,
            **dvars_dict,
        }
        # Render Dockerfile, and save to both env dir and iteration dir (under env dir)
        logger.info("Render Dockerfile from templates")
        render_and_save(
            [
                Path(spec.env_dir) / "Dockerfile",
                iteration_dir / "Dockerfile",
            ],
            path_config.dockerfile_tpl_path,
            template_vars,
            None,
        )

        # Render build.sh and run.sh from templates
        logger.info("Rendering build script from templates")
        build_script_vars = {
            "env_dir": str(Path(spec.env_dir).absolute()),
            "image_tag": tag,
            "repo_path": str(Path(spec.repo_path).absolute()),
        }
        render_and_save(
            [
                Path(spec.env_dir) / DEFAULT_DOCKER_BUILD_SCRIPT_FILENAME,
                iteration_dir / DEFAULT_DOCKER_BUILD_SCRIPT_FILENAME,
            ],
            path_config.build_script_tpl_path,
            build_script_vars,
            0o755,
        )
        logger.info("Rendering run script from templates")
        run_script_vars = {
            "repo_path": str(Path(spec.repo_path).absolute()),
            "mount_dir": env_config.mount_dir,
            "image_tag": tag,
            "test_workdir": test_workdir,
            "install_editable": dvars.install_editable,
            "pip_loc_e_dep": dvars.pip_loc_e_dep,
            "test_cmd": " ".join(dvars.test_cmd),
        }
        render_and_save(
            [
                Path(spec.env_dir) / DEFAULT_DOCKER_RUN_SCRIPT_FILENAME,
                iteration_dir / DEFAULT_DOCKER_RUN_SCRIPT_FILENAME,
            ],
            path_config.run_script_tpl_path,
            run_script_vars,
            0o755,
        )

        # Build
        logger.info(f"Building Docker image: {tag}")
        bres = docker_build(
            build_script_path=Path(spec.env_dir) / DEFAULT_DOCKER_BUILD_SCRIPT_FILENAME,
            log_path=iteration_dir / "build.log",
            image_tag=tag,
            timeout_s=agent_config.build_timeout_s,
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
                "message": bres.message,
            }
            (iteration_dir / "result.json").write_text(json.dumps(result_data, indent=2))

            return (False, build_tail, "", "build_failed")

        logger.info("Docker build successful")

        # Run
        logger.info("Running tests in container")
        rc, run_log_path, status = docker_run(
            run_script_path=Path(spec.env_dir) / DEFAULT_DOCKER_RUN_SCRIPT_FILENAME,
            log_path=iteration_dir / "run.log",
            timeout_s=agent_config.run_timeout_s,
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
            "message": f"Classification: {cls}",
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
        system_txt=system_prompt,
        task_tpl=repo_task,
        policy_prompt=policy_prompt,
        contract_json=contract,
        init_tpl_path=path_config.initial_tpl_path,
        iter_tpl_path=path_config.iterate_tpl_path,
        max_rounds=agent_config.max_rounds,
        output_retries=agent_config.output_retries,
    )

    logger.info(f"Agent completed with status: {decision.status.value}")
    if iteration_counter["count"] > 0:
        logger.info(f"Completed {iteration_counter['count']} iteration(s)")

    # Write artifacts
    logger.info("Writing output artifacts")
    env_dir = Path(spec.env_dir)
    env_dir.mkdir(parents=True, exist_ok=True)

    # Write success/failure marker
    if decision.status is DecisionStatus.PROCEED:
        logger.info("✓ Generation successful")
        (env_dir / "_SUCCESS").write_text("")
    else:
        logger.warning(f"✗ Generation refused: {decision.reason}")
        (env_dir / "_FAILURE").write_text("")

    # Note: build.sh and run.sh are already generated in the last iteration
    logger.debug(f"build.sh and run.sh available at {env_dir}")

    # Write summary
    write_summary(env_dir, spec, decision)
    logger.debug(f"Wrote summary.md to {env_dir}")

    # Write final decision JSON (at root level)
    decision_json = env_dir / DECISION_JSON_FILENAME
    decision_data = {
        "status": decision.status.value,
        "reason": decision.reason,
        "evidence": decision.evidence,
        "variables": asdict(decision.variables) if decision.variables else None,
    }
    decision_json.write_text(json.dumps(decision_data, indent=2))
    logger.debug(f"Wrote {DECISION_JSON_FILENAME} to {env_dir}")

    logger.info(f"Environment setup complete for {spec.env_id}")
    if iteration_counter["count"] > 0:
        logger.info(f"Iteration artifacts saved to: {env_dir / 'iterations'}")

    return decision
