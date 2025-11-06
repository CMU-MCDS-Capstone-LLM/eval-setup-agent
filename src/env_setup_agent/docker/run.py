"""Docker run operations."""

import os
import subprocess
from pathlib import Path
from typing import Tuple


def docker_run(
    image_tag: str,
    repo_path: Path,
    mount_dir: str,
    env_dir: Path,
    timeout_s: int = 1800
) -> Tuple[int, str, str]:
    """
    Run tests in a Docker container.

    Args:
        image_tag: Docker image tag to run
        repo_path: Path to repository on host
        mount_dir: Mount path inside container
        env_dir: Environment directory for logs
        timeout_s: Run timeout in seconds

    Returns:
        Tuple of (return_code, log_path, status)
        status is "ok" or "timeout"
    """
    log_path = env_dir / "run.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{repo_path}:{mount_dir}",
        "--user", f"{os.getuid()}:{os.getgid()}",
        image_tag
    ]

    with log_path.open("w") as logf:
        proc = subprocess.Popen(
            cmd,
            stdout=logf,
            stderr=subprocess.STDOUT
        )
        try:
            rc = proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            return -1, str(log_path), "timeout"

    return rc, str(log_path), "ok"
