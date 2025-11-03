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
    
    def __init__(self, github_token: str):
        self.github_token = github_token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        })
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

    def get_commit_info(self, repo: str, commit_sha: str) -> Dict:
        """
        Get all commit information including metadata, timestamp, and Python version upper bound.
        Returns a dictionary with all the relevant information.
        """
        metadata = self._get_commit_metadata(repo, commit_sha)
        timestamp = self._get_commit_timestamp(repo, commit_sha)
        
        result = {
            "repo": repo,
            "commit_sha": commit_sha,
            "timestamp": timestamp,
            "python_upper_bound": None
        }

        result["python_upper_bound"] = self._infer_python_upper_bound(timestamp)

        if result["python_upper_bound"] is None:
            raise ValueError(f"Failed to get commit info for commit {commit_sha} in repo {repo}")
            
        return result

if __name__ == "__main__":
    github_token = os.getenv("GITHUB_TOKEN")
    fetcher = CommitInfoFetcher(github_token)
    print(fetcher.get_commit_info(
        repo="spacetelescope/pysynphot",
        commit_sha="5b80ada45d2eb5fcdcca8959d073713ab3e84c7b"
    ))
