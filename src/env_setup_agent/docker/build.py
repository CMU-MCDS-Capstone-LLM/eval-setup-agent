"""Docker build operations."""

import subprocess
from pathlib import Path
from ..core.enums import FailureReason
from ..core.models import BuildResult


def docker_build(
    build_script_path: Path,
    log_path: Path,
    image_tag: str,
    timeout_s: int = 1800
) -> BuildResult:
    """
    Build a Docker image using BuildKit by executing build.sh script.

    Args:
        env_dir: Environment directory containing build.sh
        image_tag: Tag for the built image
        repo_path: Repository path (build context)
        timeout_s: Build timeout in seconds

    Returns:
        BuildResult with success status and log path
    """
    assert build_script_path.exists(), f"build.sh not found at {build_script_path}"
    assert build_script_path.is_absolute(), f"build_script must be absolute path: {build_script_path}"

    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("w") as logf:
        proc = subprocess.Popen(
            [str(build_script_path)],
            stdout=logf,
            stderr=subprocess.STDOUT
        )
        try:
            rc = proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            return BuildResult(
                False,
                image_tag,
                str(log_path),
                FailureReason.DOCKER_TIMEOUT,
                "build timeout"
            )

    if rc != 0:
        return BuildResult(
            False,
            image_tag,
            str(log_path),
            FailureReason.BUILD_FAILED,
            "docker build failed"
        )

    return BuildResult(True, image_tag, str(log_path))
