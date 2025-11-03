"""Aggregate facts about a repository."""

from pathlib import Path
from typing import Optional, Tuple
from ..core.models import Facts
from .tests_detector import find_tests
from .python_version import detect_python_version
from .dep_files import find_dependency_files
from .sys_pkgs import infer_system_packages
from .services import detect_service_indicators


def gather_facts(
    repo_path: Path,
    commit_date_cap: Optional[Tuple[int, int]] = None
) -> Facts:
    """
    Gather all facts about a repository.

    Args:
        repo_path: Path to repository
        commit_date_cap: Optional (major, minor) Python version cap based on commit date

    Returns:
        Facts dataclass with all discovered information
    """
    # Find tests
    tests_found, test_subdir = find_tests(repo_path)

    # Detect Python version constraints
    python_constraints, python_cap_minor = detect_python_version(repo_path, commit_date_cap)

    # Find dependency files
    dep_manifests, pip_plan = find_dependency_files(repo_path)

    # Infer system packages
    sys_packages = infer_system_packages(repo_path)

    # Detect service indicators
    service_indicators = detect_service_indicators(repo_path)

    # Determine if editable install is appropriate
    has_setup_py = (repo_path / "setup.py").exists()
    has_pyproject = (repo_path / "pyproject.toml").exists()
    allow_editable = has_setup_py or has_pyproject

    return Facts(
        tests_found=tests_found,
        python_constraints=python_constraints,
        python_cap_minor=python_cap_minor,
        dep_manifests=dep_manifests,
        pip_plan=pip_plan,
        sys_packages=sys_packages,
        service_indicators=service_indicators,
        test_subdir=test_subdir or ".",
        allow_editable=allow_editable,
    )
