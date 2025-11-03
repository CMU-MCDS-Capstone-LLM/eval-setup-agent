"""Infer system packages (APT) from Python dependencies."""

from pathlib import Path
from typing import List, Set
import re


# Mapping of Python packages to required APT packages
PYTHON_TO_APT = {
    # Cryptography & SSL
    "cryptography": ["libssl-dev", "libffi-dev"],
    "pyopenssl": ["libssl-dev"],
    "pycrypto": ["libssl-dev"],
    "pycryptodome": ["libssl-dev"],

    # XML processing
    "lxml": ["libxml2-dev", "libxslt1-dev"],
    "defusedxml": ["libxml2-dev"],

    # Images
    "pillow": ["libjpeg-dev", "libpng-dev", "libfreetype6-dev"],
    "opencv-python": ["libgl1", "libglib2.0-0"],

    # Databases
    "psycopg2": ["libpq-dev"],
    "psycopg2-binary": [],  # Binary, no system deps needed
    "mysqlclient": ["libmysqlclient-dev"],
    "pymysql": [],  # Pure Python

    # Scientific computing
    "numpy": ["libopenblas-dev", "gfortran"],
    "scipy": ["libopenblas-dev", "gfortran", "libblas-dev", "liblapack-dev"],
    "pandas": ["libopenblas-dev"],

    # Compression
    "python-snappy": ["libsnappy-dev"],
    "python-lzo": ["liblzo2-dev"],

    # YAML with C bindings
    "pyyaml": ["libyaml-dev"],

    # Other
    "uwsgi": ["libpcre3-dev"],
    "cffi": ["libffi-dev"],
    "greenlet": [],  # Usually builds fine
}


def extract_dependencies_from_requirements(repo_path: Path) -> Set[str]:
    """Extract dependency names from requirements files."""
    deps = set()

    for req_file in ["requirements.txt", "requirements-dev.txt", "requirements/base.txt",
                      "requirements/production.txt", "requirements/test.txt"]:
        req_path = repo_path / req_file
        if req_path.exists():
            try:
                content = req_path.read_text(errors="ignore")
                for line in content.splitlines():
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue
                    # Extract package name (before ==, >=, etc.)
                    match = re.match(r"^([a-zA-Z0-9_-]+)", line)
                    if match:
                        deps.add(match.group(1).lower())
            except Exception:
                pass

    return deps


def extract_dependencies_from_pyproject(repo_path: Path) -> Set[str]:
    """Extract dependency names from pyproject.toml."""
    deps = set()
    pyproject = repo_path / "pyproject.toml"

    if not pyproject.exists():
        return deps

    try:
        import tomllib
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)

        # Check project.dependencies
        if "project" in data and "dependencies" in data["project"]:
            for dep in data["project"]["dependencies"]:
                match = re.match(r"^([a-zA-Z0-9_-]+)", dep)
                if match:
                    deps.add(match.group(1).lower())

        # Check tool.poetry.dependencies
        if "tool" in data and "poetry" in data["tool"]:
            poetry = data["tool"]["poetry"]
            if "dependencies" in poetry:
                for dep in poetry["dependencies"]:
                    if dep != "python":
                        deps.add(dep.lower())

    except Exception:
        pass

    return deps


def extract_dependencies_from_setup_py(repo_path: Path) -> Set[str]:
    """Extract dependency names from setup.py."""
    deps = set()
    setup_py = repo_path / "setup.py"

    if not setup_py.exists():
        return deps

    try:
        content = setup_py.read_text(errors="ignore")
        # Look for install_requires list
        match = re.search(r'install_requires\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if match:
            requires_content = match.group(1)
            for dep_match in re.finditer(r'["\']([a-zA-Z0-9_-]+)', requires_content):
                deps.add(dep_match.group(1).lower())
    except Exception:
        pass

    return deps


def infer_system_packages(repo_path: Path) -> List[str]:
    """
    Infer required system packages from Python dependencies.

    Args:
        repo_path: Path to repository

    Returns:
        List of APT package names
    """
    # Collect all Python dependencies
    all_deps = set()
    all_deps.update(extract_dependencies_from_requirements(repo_path))
    all_deps.update(extract_dependencies_from_pyproject(repo_path))
    all_deps.update(extract_dependencies_from_setup_py(repo_path))

    # Map to system packages
    sys_packages = set()
    for dep in all_deps:
        if dep in PYTHON_TO_APT:
            sys_packages.update(PYTHON_TO_APT[dep])

    return sorted(sys_packages)
