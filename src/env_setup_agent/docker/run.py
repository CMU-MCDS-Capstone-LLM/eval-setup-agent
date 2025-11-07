"""Docker run operations."""

import subprocess
from pathlib import Path
from typing import Tuple


def docker_run(
    run_script_path: Path,
    log_path: Path,
    timeout_s: int = 1800
) -> Tuple[int, str, str]:
    """
    Run tests in a Docker container by executing run.sh script.

    Args:
        env_dir: Environment directory for logs and run.sh
        timeout_s: Run timeout in seconds

    Returns:
        Tuple of (return_code, log_path, status)
        status is "ok" or "timeout"
    """
    assert run_script_path.exists(), f"run.sh not found at {run_script_path}"
    assert run_script_path.is_absolute(), f"run_script must be absolute path: {run_script_path}"

    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("w") as logf:
        proc = subprocess.Popen(
            [str(run_script_path)],
            stdout=logf,
            stderr=subprocess.STDOUT
        )
        try:
            rc = proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            return -1, str(log_path), "timeout"

    return rc, str(log_path), "ok"
