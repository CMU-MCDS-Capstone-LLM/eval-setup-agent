# Environment Setup Agent

AI-powered agent that automatically generates Docker test environments for Python repositories. Analyzes codebases using Claude AI to determine dependencies, Python versions, and test configurations, then produces working Dockerfiles and scripts.

## Overview

The agent scans a Python repository and generates:

- Dockerfile with correct Python version and dependencies
- Build and run scripts for testing
- Iteratively fixes build/runtime errors until tests run successfully

**Key capabilities:**

- Detects tests, dependencies, and required system packages
- Infers Python version from commit date and project constraints
- Self-corrects through multiple build/test iterations (max 3 rounds)
- Provides evidence-based decisions with full traceability

## Installation

**Prerequisites:** Python 3.11+, Docker, GitHub token

```bash
pip install -e .

export GITHUB_TOKEN="your_github_token"
```

## Usage

**1. Create a config file** (`config.yaml`):

```yaml
repository:
  env_id: "org_repo__commit_hash"
  repo_name: "org/repo"
  commit_sha: "full_commit_sha"
  repo_path: "/absolute/path/to/repo"
  env_dir: "/absolute/path/to/output"

agent:
  model: null  # defaults to claude-sonnet-4-5
  max_rounds: 3
  build_timeout_s: 1800
  run_timeout_s: 1800
```

**2. Run the agent:**

```bash
env-setup-agent config.yaml
```

**3. Check outputs:**

```bash
ls /path/to/output/
# Dockerfile, build.sh, run.sh, decision.json, summary.md, _SUCCESS
```

## Output Structure

```
env_dir/
├── Dockerfile              # Generated Docker environment
├── build.sh                # Build script (executable)
├── run.sh                  # Test execution script (executable)
├── decision.json           # Agent's decision and variables
├── summary.md              # Human-readable summary
├── env_setup_agent.log     # Detailed execution log
├── _SUCCESS or _FAILURE    # Status marker
└── iterations/             # Per-iteration artifacts
    └── round_N/
        ├── decision.json, Dockerfile, build.sh, run.sh
        ├── build.log, run.log
        └── result.json
```

## How It Works

1. **Analysis**: Claude agent scans repository (read-only) to identify tests, dependencies, Python constraints
2. **Generation**: Produces `DockerVars` JSON with python version, apt packages, pip deps, test command
3. **Build & Test**: Renders Dockerfile, builds image, runs tests
4. **Iteration**: If failures occur, agent analyzes logs and refines variables (up to max_rounds)
5. **Output**: Saves final artifacts or refuses with reason

**Agent decisions:**

- `PROCEED`: Provides complete variables to generate environment
- `REFUSE`: Declines with reason (no tests, external services required, policy violation, etc.)

## Decision JSON Schema

```json
{
  "status": "proceed" | "refuse",
  "reason": "optional explanation",
  "evidence": {
    "tests_exist": ["found pytest in tests/ directory"],
    "python_version_constraints": ["CI tests Python 3.8"],
    "dependency_manifests": ["requirements.txt found"]
  },
  "variables": {
    "python_version_tag": "3.9.19-slim",
    "test_worksubdir": ".",
    "project_apt_packages": ["gcc", "libssl-dev", "libffi-dev"],
    "env_vars": {"SQL_SERVER": "sqlite"},
    "pip_deps": ["-r requirements.txt", "-r requirements-dev.txt"],
    "install_editable": true,
    "pip_loc_e_dep": ".[extras]",
    "test_cmd": ["pytest", "-v", "tests"]
  }
}
```

## Configuration Reference

**Repository fields** (all required, absolute paths):

- `env_id`: Unique identifier
- `repo_name`: GitHub `org/repo` format
- `commit_sha`: Full commit hash
- `repo_path`: Cloned repository location
- `env_dir`: Output directory

**Agent fields** (optional):

- `model`: Claude model (default: `claude-sonnet-4-5-20250929`)
- `max_rounds`: Max iterations (default: 3)
- `build_timeout_s`: Build timeout (default: 1800)
- `run_timeout_s`: Test timeout (default: 1800)

**Environment fields** (optional):

- `app_user`: Docker user (default: `appuser`)
- `mount_dir`: Container mount point (default: `/workspace`)

**Custom templates** (optional):

```yaml
paths:
  system_prompt_path: "/path/to/system.md"
  dockerfile_tpl_path: "/path/to/dockerfile.template.j2"
  # ... other paths (see src/env_setup_agent/resources/configs/)
```

## Example

See `demo/new-example/` for a complete working example:

```bash
./demo/new-example/run_example.sh
```

Example output at: `demo/new-example/envs/alice-biometrics_petisco__*/`

## Project Structure

```
src/env_setup_agent/
├── cli.py                  # CLI entry point
├── runflow.py              # Main orchestration
├── agent/claude_runner.py  # Claude SDK integration
├── core/                   # Models, schema, enums
├── docker/                 # Build/run/classify
├── templating/             # Jinja2 rendering
├── config/                 # Config loading
├── adapters/               # GitHub API, etc.
└── resources/configs/      # Default prompts & templates
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Format code
ruff format .
ruff check .
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Build timeout | Increase `build_timeout_s` in config |
| Agent refuses | Check `decision.json` and logs for refusal reason |
| Build failures | Examine `iterations/round_N/build.log` |
| Missing token | Set `GITHUB_TOKEN` environment variable |

## Dependencies

- **claude-agent-sdk** - Claude AI integration
- **jinja2** - Template rendering
- **jsonschema** - Validation
- **pyyaml** - Config parsing

## TODO

- [ ] Run same repo multiple time, and expect all runs to succeed. If one failed, check why.
  
  This can help discover subtle issues, like agent has a low probability of misunderstanding the contract

- [ ] > Sample 14 repos to generate, and manually review the successful and failed cases' env setup.

  This is meant to explore more unexpected cases that our prompt failed to cover.

- [ ] Make the prompt more detailed to avoid unneeded failure

  We need to expand and tune the prompt based on our old ones. Check out [the common prompting techniques](https://www.promptingguide.ai/techniques)

- [ ] Need to show the agent the generated dockerfile, build.sh, and run.sh for better context

  - [ ] Add more examples of
    - external services
    -

- [ ] Add a comment on what's the current progress and next step, or why stucked, when failed due to max round exceeded

- [x] Add descriptions for each field in contract.json (description + example)

- [ ] Switch from json to toml

- [ ] Refuse also when we need are in a monorepo, and a single pytest command won't be enough to run the test. For example, there are multiple python repos where each repo need a different configuration, such as two python microservices that requires different versions of python and different (maybe even conflicting) dependencies. Note that monorepo alone is not a sufficient reason to refuse: if you can simply configure all dependencies under a single python interpreter version, and run pytest directly in monorepo root folder, it's still fine.

- [ ] Add an abstraction of the generated env (like pymigbench's Migration class), so that it's easier to integrate into pipeline

- [x] Format python code, and autoformat in lazyvim

- [x] don't use separate variables `test_workdir`, `mount_dir`. Assume test runs in subfolder relative to repo root. Thus, agent only supplies a decision of `test_worksubdir`, and we manually join it with `mount_dir`

- [x] Fill template sometimes cram two lines together

  E.g. two RUN commands are crammed into one line due to incorrect variable expansion

  ```Dockerfile
  RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
      apt-get update && apt-get install -y --no-install-recommends \
        build-essential pkg-config git ca-certificates \
      && rm -rf /var/lib/apt/lists/*RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
      apt-get update && apt-get install -y --no-install-recommends \      build-essential \      libssl-dev \      libffi-dev \      libyaml-dev \    && rm -rf /var/lib/apt/lists/*
  ```

- [x] Render all templates using the same env (StrictUndefined)

- [x] Manually add pytest, pytest-cov, coverage as repo env deps

- [x] If `pip install -e .` is needed, let's do that in the run script instead of the build script.

  In build script, we bind-mount repo, install the dependencies

  When we want to run the container, we pass in something like

  ```python
  #!/usr/bin/env bash
  set -euo pipefail

  # Run tests in container
  docker run --rm \
    -v "/home/eiger/CMU/2025_Spring/11634_Capstone/playground/eval_env_setup/demo/new-example/repos/alice-biometrics_petisco__9abf7b1f6ef8c55bdddcb9a5c2eff513f6a93130":"/workspace" \
    --user "$(id -u):$(id -g)" \
    envsetup/alice-biometrics_petisco__9abf7b1f6ef8c55bdddcb9a5c2eff513f6a93130:tests \
    bash -lc "pip install -e .[fixtures,rabbitmq,pymongo,elastic,sqlalchemy,fastapi,slack,redis,flask] && python -m pytest"
  ```

  You CAN pip install locally during build time by switching to ROOT user. However, you shouldn't do that. This is because the installation at build time will generate an `<xxx>.egg.info` folder under the repo. However, at runtime, we may map into the container a fresh copy of the repo on host at a different location than the one used in build time, meaning metadata like `<xxx>.egg.info` may not be present in the repo at runtime.

- [x] The current dockerfile context is a bit too broad

  It use the entire data folder. This can be problem when we download multiple repos in the data folder, since docker build need to copy the entire context folder into its own workspace.

  We can simply use the repo root as context like this

  ```bash
  docker build -f <data folder>/envs/<repo id>/Dockerfile -t <repo tag> <data folder>/repos/<repo id>
  ```

  This is because all we need from the context is to map repo into container during build

- [x] Execute the actual build and run shell script, instead of using a custom string in python

- [x] Remove unnecessary code that are unrelated to the purpose of generation

  - e.g. data_root, the whole repo index thing
- [x] Modularize the save to env folder and iteration folder logic, and reuse for dockerfile, build.sh, run.sh

- [x] Run docker as app_user as well.

- [x] Generate run.sh and build.sh separately

- [x] Don't copy the repo into image. Instead map it to the image

  Try a manual example first

- [x] Read through testing agent codebase

- [x] Read through coding agent codebase
