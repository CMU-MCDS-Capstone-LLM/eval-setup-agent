"""Detect test files and directories in a repository."""

from pathlib import Path
from typing import List, Tuple, Optional


def find_tests(repo_path: Path) -> Tuple[List[str], Optional[str]]:
    """
    Find test files and determine test subdirectory.

    Args:
        repo_path: Path to repository root

    Returns:
        Tuple of (list of test file paths, test subdirectory or None)
    """
    tests_found: List[str] = []
    test_subdir: Optional[str] = None

    # Look for tests/ directory
    tests_dir = repo_path / "tests"
    if tests_dir.exists() and tests_dir.is_dir():
        test_subdir = "tests"
        for pattern in ["test_*.py", "*_test.py"]:
            tests_found.extend([str(p.relative_to(repo_path)) for p in tests_dir.rglob(pattern)])

    # Look for test files in root
    for pattern in ["test_*.py", "*_test.py"]:
        tests_found.extend([str(p.relative_to(repo_path)) for p in repo_path.glob(pattern)])

    # Check for pytest in CI files
    ci_indicators = []
    for ci_file in [".github/workflows/*.yml", ".github/workflows/*.yaml", ".gitlab-ci.yml", ".travis.yml"]:
        for p in repo_path.glob(ci_file):
            if p.is_file():
                content = p.read_text(errors="ignore")
                if "pytest" in content:
                    ci_indicators.append(str(p.relative_to(repo_path)))

    # If CI mentions pytest but no tests found, still note it
    if ci_indicators and not tests_found:
        tests_found = ci_indicators

    return tests_found, test_subdir
