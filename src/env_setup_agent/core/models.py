"""Core data models for env_setup_agent."""

from dataclasses import dataclass, field
from enum import Enum
from os import stat
from pathlib import Path
from typing import Dict, Optional

from env_setup_agent.consts.common import DECISION_JSON_FILENAME

from ..consts import FAILURE_FLAG_FILENAME, SUCCESS_FLAG_FILENAME
from .enums import DecisionStatus, FailureReason

# TODO: May need to define classmethod from_dict like what we did wiht EnvConfig


@dataclass
class RepoSpec:
    """Specification for a repository to process."""

    env_id: str
    repo_name: str  # org/repo
    commit_sha: str
    repo_path: str  # data/repos/<env_id>
    env_dir: str  # data/envs/<env_id>


@dataclass
class DockerVars:
    """Variables for the Dockerfile template (LLM-analyzed only)."""

    python_version_tag: str
    test_worksubdir: str
    project_apt_packages: list[str]
    env_vars: Dict[str, str]
    pip_deps: list[str]
    install_editable: bool
    pip_loc_e_dep: Optional[str]
    test_cmd: list[str]


@dataclass
class Decision:
    """Agent decision with optional variables."""

    status: DecisionStatus
    reason: str | None
    variables: DockerVars | None
    evidence: Dict[str, list[str]] = field(default_factory=dict)


def generate_dummy_decision() -> Decision:
    status = DecisionStatus.PROCEED
    reason = None
    variables = DockerVars(
        python_version_tag="3.11.13-slim",
        test_worksubdir=".",
        project_apt_packages=["libssl"],
        env_vars={"MY_ENV_VAR": "foobar"},
        pip_deps=["numpy", "pandas"],
        install_editable=True,
        pip_loc_e_dep=".[fixture]",
        test_cmd=["python", "-m", "pytest"],
    )
    evidence = {}
    return Decision(status=status, reason=reason, variables=variables, evidence=evidence)


@dataclass
class BuildResult:
    """Result of a Docker build operation."""

    success: bool
    image_tag: str
    log_path: str
    failure_reason: Optional[FailureReason] = None
    message: str = ""


@dataclass
class TestResult:
    """Result of running tests in the container."""

    status: str  # "ok" | "pytest_failed" | "deps_error" | "build_failed"
    returncode: int
    log_path: str
    failure_reason: Optional[FailureReason] = None
    message: str = ""
