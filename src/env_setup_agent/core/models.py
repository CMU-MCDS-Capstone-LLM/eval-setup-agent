"""Core data models for env_setup_agent."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from .enums import Status, FailureReason

# TODO: May need to define classmethod from_dict like what we did wiht EnvConfig

@dataclass
class RepoSpec:
    """Specification for a repository to process."""
    env_id: str
    repo_name: str        # org/repo
    commit_sha: str
    repo_path: str        # data/repos/<env_id>
    env_dir: str          # data/envs/<env_id>


@dataclass
class Facts:
    """Facts discovered about the repository."""
    tests_found: List[str]
    python_constraints: List[str]
    python_cap_minor: Tuple[int, int]
    dep_manifests: List[str]
    pip_plan: List[str]
    sys_packages: List[str]
    service_indicators: List[str]
    test_subdir: str
    allow_editable: bool


@dataclass
class DockerVars:
    """Variables for the Dockerfile template (LLM-analyzed only)."""
    python_version_tag: str
    test_worksubdir: str
    project_apt_packages: List[str]
    env_vars: Dict[str, str]
    pip_deps: List[str]
    install_editable: bool
    pip_loc_e_dep: Optional[str]
    test_cmd: List[str]


@dataclass
class Decision:
    """Agent decision with optional variables."""
    status: Status
    reason: Optional[str]
    variables: Optional[DockerVars]
    evidence: Dict[str, List[str]] = field(default_factory=dict)

def generate_dummy_decision() -> Decision:
    status = Status.PROCEED
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
    return Decision(
        status=status,
        reason=reason,
        variables=variables,
        evidence=evidence
    )


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
    status: str             # "ok" | "pytest_failed" | "deps_error" | "build_failed"
    returncode: int
    log_path: str
    failure_reason: Optional[FailureReason] = None
    message: str = ""
