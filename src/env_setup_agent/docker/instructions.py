"""Generate run instructions script."""

from pathlib import Path


def write_run_instructions(
    env_dir: Path,
    image_tag: str,
    data_root: Path,
    mount_dir: str,
    env_id: str
) -> None:
    """
    Write a run_instructions.sh script.

    Args:
        env_dir: Environment directory
        image_tag: Docker image tag
        data_root: Root data directory
        mount_dir: Mount path inside container
        env_id: Environment identifier
    """
    script = f"""#!/usr/bin/env bash
set -euo pipefail

# Build the Docker image
export DOCKER_BUILDKIT=1
docker build -f data/envs/{env_id}/Dockerfile -t {image_tag} data/

# Run tests in container
docker run --rm \\
  -v "$PWD/data/repos/{env_id}":"{mount_dir}" \\
  --user "$(id -u):$(id -g)" \\
  {image_tag}
"""

    script_path = env_dir / "run_instructions.sh"
    script_path.write_text(script)
    script_path.chmod(0o755)
