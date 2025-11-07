## TODO

- [ ] Make the prompt more detailed to avoid unneeded failure

  We need to expand and tune the prompt based on our old ones. Check out [the common prompting techniques](https://www.promptingguide.ai/techniques)

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

- [ ] Need to show the agent the generated dockerfile, build.sh, and run.sh for better context

- [x] Manually add pytest, pytest-cov, coverage as repo env deps

- [ ] If `pip install -e .` is needed, let's do that in the run script instead of the build script.

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

- [ ] The current dockerfile context is a bit too broad

  It use the entire data folder. This can be problem when we download multiple repos in the data folder, since docker build need to copy the entire context folder into its own workspace.

  We can simply use the repo root as context like this

  ```bash
  docker build -f <data folder>/envs/<repo id>/Dockerfile -t <repo tag> <data folder>/repos/<repo id>
  ```

  This is because all we need from the context is to map repo into container during build

- [ ] Execute the actual build and run shell script, instead of using a custom string in python

- [ ] Remove unnecessary code that are unrelated to the purpose of generation

  - e.g. data_root, the whole repo index thing

- [x] Generate run.sh and build.sh separately

- [x] Don't copy the repo into image. Instead map it to the image

  Try a manual example first

- [x] Read through testing agent codebase

- [x] Read through coding agent codebase

## How to set up environment to run evaluation on PyMigBench?

There are two pain points

1. Unlike SWE-Bench, PyMigBench doesn't give instruction on how to set up env for each data point.

2. Testing agent and coding agent need to use the same environment, so we must make the env into a docker image or dockerfile somehow.

## Prereq knowledge

### Test only on subset of PyMigBench

We won't be testing on all data points in PyMigBench, and we assume this in the rest of this doc unless specified. In specific, we only consider repos with the following properties

- The repo must have at least one unit test, since that allows us to test if the env is set up correctly, however minimal the test is.

  This is around 2/3 of the benchmark.

But we will provide a better way to set up environment. The original pymigbench paper's env discovery method only successfully set up env for 46 migrations

### What counts as env setup?

We will automatically set up the following dependencies for each repo in PyMigBench

1. Python intepreter

  e.g. python 3.11, python 2.7

2. System packages

  e.g. postgresql

3. Python packages

  e.g. Flask

Note that these dependencies doesn't count

- platform: we assume linux x86_64, the most common one.

### What counts as successful env setup?

For each repo in PyMigBench, we assume env setup is successful if the following two conditions are met

- installation of the dependencies raise no error (or error is fixed)

- existing unit tests in the repo runs successfully on multiple runs

  we require multiple runs to avoid flakiness, where ephemeral failure happens.

## Env setup process

### Env discovery

The original pymigbench paper already proposes a heuristic algo to discover these dependencies

- Python version

- System packages

However, the way python version is discovered doesn't make use of codebase content (e.g. one that hide in docker file), and system packages is ignored entirely, meaning projects such one those depending on external local database setup won't work.

We will combine llm and heuristic algo to discover env smartly, using either a workflow or agent to discover all three types of dependencies mentioned above.

### Env installtion & testing

We will start with a minimal linux docker image, either on ec2 or on local laptop, in which our algorithm will set up environment.

We will install the discovered env, run the tests with pytest, and iterate based on error log if any.

**What count as failed to setup**: We require the env installation to be completed with a given cost / step / token consumption, and consider env setup as failed if exceeding such threshold.

### Env saving & reusing

To save env, we will export the environment into a docker image.

To reuse env, we will upload the docker image to a single ECR repo, and use tags to differentiate images for diff data points. Since full eval on pymigbench will be conducted on AWS EC2 instances, we can simply pull from ECR to reuse the env with no cost (assume same region).

> Note that this does **requires all AWS services to be in the same region**. We will use **us-east-2** for experiment.

We can customize SWE Agent to start from existing docker image.

## Notes

- We must **run all aws services within the same region**. We will use **us-east-2** for experiment.

- dependencies added by migration is not installed. For example, if we migrate from pandas to polors, we will only install pandas, and not polors. Our coding agent is expected to install such dependencies as it performs migration.

# env_setup_agent

AI agent for generating reproducible Docker environments for Python repositories.

## Overview

`env_setup_agent` uses Claude Agent SDK to automatically generate Dockerfiles for Python projects. The agent:

1. Scans repositories (read-only) to detect tests, dependencies, and constraints
2. Generates validated JSON variables for a fixed Dockerfile template
3. Builds the image using BuildKit with bind-mounted dependencies
4. Iterates on failures (build/test logs) until success or limits

## Features

- **Template-based**: Uses Jinja2 templates, not freeform Dockerfile generation
- **Read-only scanning**: Agent can only read files, not modify them
- **BuildKit optimization**: Bind-mounts repo during build for fast iterations
- **Iterative refinement**: Agent adjusts based on build/test logs
- **Deterministic outputs**: Success writes Dockerfile + run script + summary

## Installation

```bash
cd env_setup_agent
pip install -e .
```

### Prerequisites

- Python ≥ 3.11
- Docker with BuildKit support
- Claude API key (if required): `export CLAUDE_API_KEY=...`
  You can also the claude code cli with monthly pro subscription. The python sdk will communicate to the cli internally. This avoid using API and makes the cost more controllable (20 USD per month), at the cost of more rate-limiting

## Usage

### Command-line interface

```bash
# Scan a repository
env-setup-agent scan /path/to/repo

# Generate environment for a single repo
env-setup-agent generate \
  my-env-id \
  org/repo \
  abc123def \
  2024-01-15T12:00:00Z \
  --data-root data \
  --model claude-sonnet-4 \
  --max-rounds 3

# List all repositories
env-setup-agent list --data-root data

# Process all repositories in data/repos
env-setup-agent all --data-root data --skip-existing
```

### Python API

```python
import asyncio
from pathlib import Path
from env_setup_agent.core.models import RepoSpec
from env_setup_agent.runflow import run_one

spec = RepoSpec(
    env_id="myrepo__abc123",
    repo_name="org/myrepo",
    commit_sha="abc123",
    commit_ts_iso="2024-01-15T12:00:00Z",
    repo_path="data/repos/myrepo__abc123",
    env_dir="data/envs/myrepo__abc123"
)

decision = asyncio.run(run_one(
    spec=spec,
    python_cap_minor=(3, 11),
    prompts_dir=Path("src/env_setup_agent/agent/prompts"),
    templates_dir=Path("src/env_setup_agent/templating"),
    data_root=Path("data"),
    model=None,  # Use default
    max_rounds=3
))

if decision.status.value == "proceed":
    print(f"Success! Dockerfile at {spec.env_dir}/Dockerfile")
else:
    print(f"Refused: {decision.reason}")
```

## Directory Structure

After running, you'll have:

```
data/
├── repos/
│   └── <env_id>/           # Cloned repository
├── envs/
│   └── <env_id>/
│       ├── Dockerfile      # Generated Dockerfile
│       ├── run_instructions.sh
│       ├── decision.json
│       ├── build.log
│       ├── run.log
│       ├── summary.md
│       └── _SUCCESS or _FAILURE
└── prompts/
    └── <env_id>/
        └── prompt.md       # Optional: full prompt sent to agent
```

## Configuration

Set environment variables to configure:

```bash
export ESA_MODEL="claude-sonnet-4"
export ESA_MAX_ROUNDS=3
export ESA_BUILD_TIMEOUT=1800  # seconds
export ESA_RUN_TIMEOUT=1800
export ESA_DATA_ROOT="data"
export ESA_PROMPTS_DIR="src/env_setup_agent/agent/prompts"
export ESA_TEMPLATES_DIR="src/env_setup_agent/templating"
```

## How It Works

### 1. Detection Phase

The agent scans the repository to gather facts:

- Test files and directories
- Python version constraints (pyproject.toml, setup.py, etc.)
- Dependency manifests (requirements.txt, pyproject.toml, etc.)
- Required system packages (inferred from Python deps)
- External service indicators (docker-compose, GitHub Actions services, etc.)

### 2. Generation Phase

Claude Agent SDK (with read-only tools: Glob, Grep, Read) analyzes the repo and outputs JSON:

```json
{
  "status": "proceed",
  "variables": {
    "python_version_tag": "3.11.8-slim",
    "mount_dir": "/workspace",
    "repo_bind_src": "repos/myrepo__abc123",
    "test_workdir": "/workspace",
    "app_user": "appuser",
    "project_apt_packages": ["libssl-dev", "libffi-dev"],
    "env_vars": {"PYTHONUNBUFFERED": "1"},
    "pip_deps": ["-r requirements.txt", "pytest"],
    "install_editable": true,
    "test_cmd": ["python", "-m", "pytest"]
  }
}
```

### 3. Build Phase

The Dockerfile template is rendered with these variables using BuildKit:

```dockerfile
# syntax=docker/dockerfile:1.7
FROM python:3.11.8-slim

RUN --mount=type=bind,source=repos/myrepo__abc123,target=/workspace,rw \
    cd /workspace && \
    pip install -r requirements.txt && \
    pip install -e .
```

### 4. Test Phase

The built image runs `pytest` with the repo mounted at the same path.

### 5. Iteration

If build or tests fail with dependency errors, the agent receives logs and can revise the JSON. This continues for up to `max_rounds`.

## Policy

The agent follows these rules:

- **Proceed** only if tests can run with Python interpreter + deps + system libs
- **Refuse** if:
  - No tests found
  - External services required (unless tests self-spawn/mock them)
- No virtualenvs or services in Dockerfile
- Base image: `python:X.Y-slim` where X.Y ≤ detected upper bound

## Constraints

- Requires Docker BuildKit (`DOCKER_BUILDKIT=1`)
- Repo must be pre-cloned under `data/repos/<env_id>`
- Repo will be mounted at the same path during build and runtime
- Python 3 projects only
- Agent has read-only access (Glob, Grep, Read tools)

## Example: Single Repository

```bash
# 1. Clone repo
git clone https://github.com/org/myrepo data/repos/myrepo__abc123
cd data/repos/myrepo__abc123
git checkout abc123
cd ../../..

# 2. Generate environment
env-setup-agent generate \
  myrepo__abc123 \
  org/myrepo \
  abc123 \
  2024-01-15T12:00:00Z

# 3. Review output
cat data/envs/myrepo__abc123/summary.md

# 4. Run tests manually
bash data/envs/myrepo__abc123/run_instructions.sh
```

## Troubleshooting

### Claude SDK not available

If you see "Claude SDK not available", install it:

```bash
pip install claude-agent-sdk
```

### Build timeout

Increase timeout:

```bash
export ESA_BUILD_TIMEOUT=3600  # 1 hour
```

### Rate limiting

The agent may fail due to API rate limits. In this case, the generation aborts without saving artifacts. Retry after a delay.

### Missing system packages

If builds fail with missing system libraries, the agent should detect and add them in subsequent rounds. Check `data/envs/<env_id>/build.log` for details.

## Development

### Running tests

```bash
pip install -e ".[dev]"
pytest tests/
```

### Code formatting

```bash
black src/ tests/
```

### Type checking

```bash
mypy src/
```

## Architecture

See the design document for detailed architecture and code structure.

Key components:

- `core/`: Data models, enums, schema validation
- `config/`: Configuration management
- `detect/`: Repository scanning (tests, deps, versions)
- `agent/`: Claude Agent SDK integration with prompts
- `templating/`: Jinja2 Dockerfile template
- `docker/`: Build, run, classify operations
- `io/`: Filesystem and logging utilities
- `adapters/`: External integrations (GitHub, clock)
- `runflow.py`: Main controller
- `cli.py`: Command-line interface

## License

See LICENSE file.

## Contributing

Contributions welcome! Please open an issue or PR.
