"""Detect external service requirements."""

from pathlib import Path
from typing import List


def detect_service_indicators(repo_path: Path) -> List[str]:
    """
    Detect indicators of external service requirements.

    Args:
        repo_path: Path to repository

    Returns:
        List of service indicator descriptions
    """
    indicators = []

    # Check for docker-compose files
    compose_files = ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]
    for compose_file in compose_files:
        if (repo_path / compose_file).exists():
            indicators.append(f"docker-compose file found: {compose_file}")

    # Check GitHub Actions for service containers
    gh_workflows = repo_path / ".github" / "workflows"
    if gh_workflows.exists():
        for workflow_file in gh_workflows.glob("*.yml"):
            try:
                content = workflow_file.read_text(errors="ignore")
                if "services:" in content:
                    indicators.append(f"GitHub Actions services in: {workflow_file.name}")
            except Exception:
                pass

    # Check for Testcontainers usage
    python_files = list(repo_path.rglob("*.py"))
    for py_file in python_files[:100]:  # Limit to avoid scanning too many files
        try:
            content = py_file.read_text(errors="ignore")
            if "testcontainers" in content.lower():
                indicators.append(f"Testcontainers import in: {py_file.relative_to(repo_path)}")
                break  # One indicator is enough
        except Exception:
            pass

    # Check for unmocked database URLs or service endpoints
    env_example = repo_path / ".env.example"
    if env_example.exists():
        try:
            content = env_example.read_text(errors="ignore")
            service_vars = ["DATABASE_URL", "REDIS_URL", "MONGODB_URI", "ELASTICSEARCH_URL", "RABBITMQ_URL"]
            for var in service_vars:
                if var in content:
                    indicators.append(f"Service variable in .env.example: {var}")
        except Exception:
            pass

    # Check test files for service mocking patterns
    test_dirs = [repo_path / "tests", repo_path / "test"]
    has_mocking = False
    for test_dir in test_dirs:
        if not test_dir.exists():
            continue
        for test_file in test_dir.rglob("test_*.py"):
            try:
                content = test_file.read_text(errors="ignore")
                # Look for common mocking patterns
                if any(pattern in content for pattern in ["@mock", "unittest.mock", "pytest.fixture", "@patch"]):
                    has_mocking = True
                    break
            except Exception:
                pass
        if has_mocking:
            break

    # If we found service indicators but also mocking, note that tests might be self-contained
    if indicators and has_mocking:
        indicators.append("Mocking patterns found in tests (services may be mocked)")

    return indicators
