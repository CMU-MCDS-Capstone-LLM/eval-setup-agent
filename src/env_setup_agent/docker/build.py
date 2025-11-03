"""Docker build operations."""

import os
import subprocess
import shlex
from pathlib import Path
from ..core.enums import FailureReason
from ..core.models import BuildResult


def docker_build(
    env_dir: Path,
    image_tag: str,
    data_root: Path,
    timeout_s: int = 1800
) -> BuildResult:
    """
    Build a Docker image using BuildKit.

    Args:
        env_dir: Environment directory containing Dockerfile
        image_tag: Tag for the built image
        data_root: Root data directory (build context)
        timeout_s: Build timeout in seconds

    Returns:
        BuildResult with success status and log path
    """
    dockerfile = env_dir / "Dockerfile"
    log_path = env_dir.parent.parent / "trajectories" / env_dir.name / "build.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = f"docker build -f {shlex.quote(str(dockerfile))} -t {shlex.quote(image_tag)} {shlex.quote(str(data_root))}"
    env = os.environ.copy()
    env["DOCKER_BUILDKIT"] = "1"

    with log_path.open("w") as logf:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=logf,
            stderr=subprocess.STDOUT,
            env=env
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
