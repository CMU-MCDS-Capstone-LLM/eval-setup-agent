"""Generate run instructions script."""

from pathlib import Path


def write_build_and_run_scripts(
    env_dir: Path,
    image_tag: str,
    data_root: Path,
    mount_dir: str,
    env_id: str
) -> None:
    """
    Write separate build.sh and run.sh scripts.

    Args:
        env_dir: Environment directory
        image_tag: Docker image tag
        data_root: Root data directory
        mount_dir: Mount path inside container
        env_id: Environment identifier
    """
    # Write build.sh
    build_script = f"""#!/usr/bin/env bash
set -euo pipefail

# Build the Docker image
export DOCKER_BUILDKIT=1
docker build -f data/envs/{env_id}/Dockerfile -t {image_tag} data/
"""

    build_path = env_dir / "build.sh"
    build_path.write_text(build_script)
    build_path.chmod(0o755)

    # Write run.sh
    run_script = f"""#!/usr/bin/env bash
set -euo pipefail

# Run tests in container
docker run --rm \\
  -v "$PWD/data/repos/{env_id}":"{mount_dir}" \\
  --user "$(id -u):$(id -g)" \\
  {image_tag}
"""

    run_path = env_dir / "run.sh"
    run_path.write_text(run_script)
    run_path.chmod(0o755)
