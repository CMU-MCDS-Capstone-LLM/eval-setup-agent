"""Generate run instructions script."""

from pathlib import Path


def write_build_and_run_scripts(
    env_dir: Path,
    image_tag: str,
    mount_dir: str,
    repo_path: Path
) -> None:
    """
    Write separate build.sh and run.sh scripts.

    Args:
        env_dir: Environment directory
        image_tag: Docker image tag
        mount_dir: Mount path inside container
        repo_path: Path to the repository (used as build context and runtime mount)
    """
    # Write build.sh
    build_script = f"""#!/usr/bin/env bash
set -euo pipefail

# Build the Docker image
export DOCKER_BUILDKIT=1
docker build -f {env_dir}/Dockerfile -t {image_tag} {repo_path}
"""

    build_path = env_dir / "build.sh"
    build_path.write_text(build_script)
    build_path.chmod(0o755)

    # Write run.sh
    run_script = f"""#!/usr/bin/env bash
set -euo pipefail

# Run tests in container
docker run --rm \\
  -v "{repo_path}":"{mount_dir}" \\
  --user "$(id -u):$(id -g)" \\
  {image_tag}
"""

    run_path = env_dir / "run.sh"
    run_path.write_text(run_script)
    run_path.chmod(0o755)
