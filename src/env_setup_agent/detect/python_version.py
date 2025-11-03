"""Detect Python version constraints from repository files."""

import re
import tomllib
from pathlib import Path
from typing import List, Tuple, Optional


def extract_from_pyproject(repo_path: Path) -> Optional[str]:
    """Extract Python version constraint from pyproject.toml."""
    pyproject = repo_path / "pyproject.toml"
    if not pyproject.exists():
        return None

    try:
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)

        # Check project.requires-python
        if "project" in data and "requires-python" in data["project"]:
            return data["project"]["requires-python"]

        # Check tool.poetry.dependencies.python
        if "tool" in data and "poetry" in data["tool"]:
            poetry = data["tool"]["poetry"]
            if "dependencies" in poetry and "python" in poetry["dependencies"]:
                return poetry["dependencies"]["python"]

    except Exception:
        pass

    return None


def extract_from_setup_py(repo_path: Path) -> Optional[str]:
    """Extract Python version constraint from setup.py."""
    setup_py = repo_path / "setup.py"
    if not setup_py.exists():
        return None

    try:
        content = setup_py.read_text(errors="ignore")
        # Look for python_requires= in setup()
        match = re.search(r'python_requires\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
    except Exception:
        pass

    return None


def extract_from_setup_cfg(repo_path: Path) -> Optional[str]:
    """Extract Python version constraint from setup.cfg."""
    setup_cfg = repo_path / "setup.cfg"
    if not setup_cfg.exists():
        return None

    try:
        content = setup_cfg.read_text(errors="ignore")
        # Look for python_requires in [options]
        match = re.search(r'python_requires\s*=\s*(.+)', content)
        if match:
            return match.group(1).strip()
    except Exception:
        pass

    return None


def extract_from_classifiers(repo_path: Path) -> List[str]:
    """Extract Python version from classifiers in setup.py or pyproject.toml."""
    versions = []

    # Try pyproject.toml
    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        try:
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)

            classifiers = []
            if "project" in data and "classifiers" in data["project"]:
                classifiers = data["project"]["classifiers"]
            elif "tool" in data and "poetry" in data["tool"] and "classifiers" in data["tool"]["poetry"]:
                classifiers = data["tool"]["poetry"]["classifiers"]

            for c in classifiers:
                if "Programming Language :: Python :: 3." in c:
                    match = re.search(r"3\.(\d+)", c)
                    if match:
                        versions.append(f"3.{match.group(1)}")
        except Exception:
            pass

    # Try setup.py
    setup_py = repo_path / "setup.py"
    if setup_py.exists():
        try:
            content = setup_py.read_text(errors="ignore")
            for match in re.finditer(r"Programming Language :: Python :: 3\.(\d+)", content):
                versions.append(f"3.{match.group(0).split()[-1]}")
        except Exception:
            pass

    return versions


def parse_constraints(constraints: List[str]) -> Tuple[int, int]:
    """
    Parse version constraints and determine upper bound.

    Priority order: pyproject.toml, setup.cfg, setup.py, classifiers

    Args:
        constraints: List of constraint strings

    Returns:
        Tuple of (major, minor) version upper bound
    """
    if not constraints:
        return (3, 11)  # Default

    # Take first constraint (highest priority)
    constraint = constraints[0]

    # Parse constraint string like ">=3.8", ">=3.8,<4", "^3.8", "~=3.8"
    versions = []

    # Extract version numbers
    for match in re.finditer(r"3\.(\d+)", constraint):
        versions.append((3, int(match.group(1))))

    if not versions:
        return (3, 11)

    # If there's an upper bound (< or <=), use it
    if "<" in constraint:
        # Find highest version mentioned with <
        for i, v in enumerate(versions):
            if "<" in constraint.split(str(v[0]) + "." + str(v[1]))[0]:
                return v
        # Otherwise use the last version
        return versions[-1]

    # Otherwise use the highest mentioned version
    return max(versions, key=lambda v: v[1])


def detect_python_version(repo_path: Path, commit_date_cap: Optional[Tuple[int, int]] = None) -> Tuple[List[str], Tuple[int, int]]:
    """
    Detect Python version constraints.

    Args:
        repo_path: Path to repository
        commit_date_cap: Optional (major, minor) cap based on commit date

    Returns:
        Tuple of (constraint strings, (major, minor) upper bound)
    """
    constraints = []

    # Priority order
    for extractor in [extract_from_pyproject, extract_from_setup_cfg, extract_from_setup_py]:
        result = extractor(repo_path)
        if result:
            constraints.append(result)

    # Add classifiers as lowest priority
    classifier_versions = extract_from_classifiers(repo_path)
    if classifier_versions:
        constraints.append(" ".join(classifier_versions))

    # Parse to get upper bound
    upper_bound = parse_constraints(constraints)

    # Apply commit date cap if provided
    if commit_date_cap:
        upper_bound = min(upper_bound, commit_date_cap)

    return constraints, upper_bound
