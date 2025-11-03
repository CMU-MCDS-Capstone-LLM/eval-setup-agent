"""GitHub commit info adapter."""

from datetime import datetime
from typing import Optional, Tuple


class CommitInfoFetcher:
    """
    Adapter for fetching commit information from GitHub.

    This is a placeholder that can be replaced with your actual
    CommitInfoFetcher implementation.
    """

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize fetcher.

        Args:
            github_token: Optional GitHub API token
        """
        self.github_token = github_token

    def get_commit_date(self, repo_name: str, commit_sha: str) -> Optional[str]:
        """
        Get commit date in ISO format.

        Args:
            repo_name: Repository name (org/repo)
            commit_sha: Commit SHA

        Returns:
            ISO timestamp string or None
        """
        # Placeholder - implement with actual GitHub API call
        return None


def python_version_cap_from_date(commit_date_iso: str) -> Tuple[int, int]:
    """
    Determine Python version cap based on commit date.

    Uses a simple heuristic based on Python release dates:
    - Before 2021-10-04: 3.9
    - Before 2022-10-24: 3.10
    - Before 2023-10-02: 3.11
    - Otherwise: 3.12

    Args:
        commit_date_iso: Commit date in ISO format

    Returns:
        Tuple of (major, minor) version
    """
    try:
        dt = datetime.fromisoformat(commit_date_iso.replace("Z", "+00:00"))
    except Exception:
        return (3, 11)  # Default

    # Python version release dates
    if dt < datetime(2021, 10, 4, tzinfo=dt.tzinfo or None):
        return (3, 9)
    elif dt < datetime(2022, 10, 24, tzinfo=dt.tzinfo or None):
        return (3, 10)
    elif dt < datetime(2023, 10, 2, tzinfo=dt.tzinfo or None):
        return (3, 11)
    else:
        return (3, 12)
