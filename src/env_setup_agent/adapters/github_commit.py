"""GitHub commit info adapter."""

from datetime import datetime
from typing import Optional, Tuple

#
# class CommitInfoFetcher:
#     """
#     Adapter for fetching commit information from GitHub.
#
#     This is a placeholder that can be replaced with your actual
#     CommitInfoFetcher implementation.
#     """
#
#     def __init__(self, github_token: Optional[str] = None):
#         """
#         Initialize fetcher.
#
#         Args:
#             github_token: Optional GitHub API token
#         """
#         self.github_token = github_token
#
#     def get_commit_date(self, repo_name: str, commit_sha: str) -> Optional[str]:
#         """
#         Get commit date in ISO format.
#
#         Args:
#             repo_name: Repository name (org/repo)
#             commit_sha: Commit SHA
#
#         Returns:
#             ISO timestamp string or None
#         """
#         # Placeholder - implement with actual GitHub API call
#         return None
#
#
# def python_version_cap_from_date(commit_date_iso: str) -> Tuple[int, int]:
#     """
#     Determine Python version cap based on commit date.
#
#     Uses a simple heuristic based on Python release dates:
#     - Before 2021-10-04: 3.9
#     - Before 2022-10-24: 3.10
#     - Before 2023-10-02: 3.11
#     - Otherwise: 3.12
#
#     Args:
#         commit_date_iso: Commit date in ISO format
#
#     Returns:
#         Tuple of (major, minor) version
#     """
#     try:
#         dt = datetime.fromisoformat(commit_date_iso.replace("Z", "+00:00"))
#     except Exception:
#         return (3, 11)  # Default
#
#     # Python version release dates
#     if dt < datetime(2021, 10, 4, tzinfo=dt.tzinfo or None):
#         return (3, 9)
#     elif dt < datetime(2022, 10, 24, tzinfo=dt.tzinfo or None):
#         return (3, 10)
#     elif dt < datetime(2023, 10, 2, tzinfo=dt.tzinfo or None):
#         return (3, 11)
#     else:
#         return (3, 12)

"""
GitHub API client for downloading commits and getting parent information.
"""

import requests
import logging
from typing import Dict, Tuple
from datetime import datetime
import os

PYTHON_RELEASES = {
    (2, 0): datetime(2000, 10, 16),
    (2, 1): datetime(2001, 4, 15),
    (2, 2): datetime(2001, 12, 21),
    (2, 3): datetime(2003, 7, 29),
    (2, 4): datetime(2004, 11, 30),
    (2, 5): datetime(2006, 9, 19),
    (2, 6): datetime(2008, 10, 1),
    (2, 7): datetime(2010, 7, 3),
    (3, 0): datetime(2008, 12, 3),
    (3, 1): datetime(2009, 6, 27),
    (3, 2): datetime(2011, 2, 20),
    (3, 3): datetime(2012, 9, 29),
    (3, 4): datetime(2014, 3, 16),
    (3, 5): datetime(2015, 9, 13),
    (3, 6): datetime(2016, 12, 23),
    (3, 7): datetime(2018, 6, 27),
    (3, 8): datetime(2019, 10, 14),
    (3, 9): datetime(2020, 10, 5),
    (3, 10): datetime(2021, 10, 4),
    (3, 11): datetime(2022, 10, 24),
    (3, 12): datetime(2023, 10, 2),
    (3, 13): datetime(2024, 10, 7),
}


class CommitInfoFetcher:
    """Client for interacting with GitHub API."""

    def __init__(self, github_token: str | None):
        if github_token is None or len(github_token) == 0:
            raise RuntimeError("We require a github token to be used to access GitHub, to avoid rate limiting.")
        self.github_token = github_token
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
        )
        self.logger = logging.getLogger(__name__)

    def _get_commit_metadata(self, repo: str, commit_sha: str) -> Dict | None:
        """
        Get the metadata of commit
        """
        url = f"https://api.github.com/repos/{repo}/commits/{commit_sha}"

        try:
            response = self.session.get(url)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching commit {commit_sha} from {repo}: {e}")
            return None

    def _get_commit_timestamp(self, repo: str, commit_sha: str) -> datetime | None:
        commit_info = self._get_commit_metadata(repo, commit_sha)
        if commit_info is None:
            return None
        try:
            # example of ts_str: 2015-10-14T13:22:43Z
            ts_str = commit_info["commit"]["author"]["date"]
            ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ")
            return ts
        except KeyError as e:
            self.logger.error(f"Can't find timestamp of commit {commit_sha} from {repo}: {e}")
            return None

    def _infer_python_upper_bound(self, commit_date: datetime) -> Tuple[int, int]:
        """
        Given a datetime object, return the latest possible Python version (major, minor)
        that was released on or before that date.
        """
        if not isinstance(commit_date, datetime):
            raise TypeError("commit_date must be a datetime.datetime object")

        releases_sorted = sorted(PYTHON_RELEASES.items(), key=lambda kv: kv[1])

        upper_bound = None
        for version, release_date in releases_sorted:
            if commit_date >= release_date:
                upper_bound = version
            else:
                break

        return upper_bound or (2, 0)

    def infer_python_upper_bound_for_repo(self, repo: str, commit_sha: str) -> Tuple[int, int]:
        """
        Get all commit information including metadata, timestamp, and Python version upper bound.
        Returns a dictionary with all the relevant information.
        """
        metadata = self._get_commit_metadata(repo, commit_sha)
        timestamp = self._get_commit_timestamp(repo, commit_sha)

        if timestamp is None:
            raise ValueError(f"Failed to get commit info for commit {commit_sha} in repo {repo}")

        result = self._infer_python_upper_bound(timestamp)

        if result is None:
            raise ValueError(f"Failed to get commit info for commit {commit_sha} in repo {repo}")

        return result


if __name__ == "__main__":
    github_token = os.getenv("GITHUB_TOKEN")
    fetcher = CommitInfoFetcher(github_token)
    print(
        fetcher.infer_python_upper_bound_for_repo(
            repo="spacetelescope/pysynphot", commit_sha="5b80ada45d2eb5fcdcca8959d073713ab3e84c7b"
        )
    )
