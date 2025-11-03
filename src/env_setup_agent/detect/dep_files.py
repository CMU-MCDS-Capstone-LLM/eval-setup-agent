"""Detect dependency manifest files."""

from pathlib import Path
from typing import List, Tuple


def find_dependency_files(repo_path: Path) -> Tuple[List[str], List[str]]:
    """
    Find dependency manifest files and generate pip install plan.

    Args:
        repo_path: Path to repository root

    Returns:
        Tuple of (list of manifest file paths, pip install plan)
    """
    manifests = []
    pip_plan = []

    # Check for various dependency files in priority order
    candidates = [
        ("requirements.txt", ["requirements.txt"]),
        ("requirements-dev.txt", ["requirements-dev.txt"]),
        ("requirements/base.txt", ["requirements/base.txt"]),
        ("requirements/production.txt", ["requirements/production.txt"]),
        ("requirements/test.txt", ["requirements/test.txt"]),
        ("pyproject.toml", []),  # Handled separately
        ("setup.py", []),  # Handled separately
        ("setup.cfg", []),  # Handled separately
        ("Pipfile", []),  # Pipenv
        ("poetry.lock", []),  # Poetry
    ]

    for filename, install_cmd in candidates:
        filepath = repo_path / filename
        if filepath.exists():
            manifests.append(filename)
            if install_cmd:
                for req in install_cmd:
                    pip_plan.append(f"-r {req}")

    # Check for pyproject.toml
    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        if "pyproject.toml" not in manifests:
            manifests.append("pyproject.toml")

    # Check for setup.py or setup.cfg (indicates installable package)
    has_setup_py = (repo_path / "setup.py").exists()
    has_setup_cfg = (repo_path / "setup.cfg").exists()

    if has_setup_py and "setup.py" not in manifests:
        manifests.append("setup.py")

    if has_setup_cfg and "setup.cfg" not in manifests:
        manifests.append("setup.cfg")

    # If no requirements files but has setup.py/pyproject.toml, plan to install package
    if not pip_plan and (has_setup_py or pyproject.exists()):
        # Will be handled as editable install or regular install
        pass

    # Add pytest as a basic requirement if not in a requirements file
    # (will be refined by agent)
    if not any("requirements" in m for m in manifests):
        pip_plan.append("pytest")

    return manifests, pip_plan
