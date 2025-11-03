# Running env_setup_agent from YAML Config

This guide explains how to run `env_setup_agent` using YAML configuration files with comprehensive logging.

## Overview

The new `env-setup-agent-from-config` command allows you to:
- Configure the agent via YAML files
- Use relative paths (resolved from repository root)
- Generate output at custom locations
- Get logs both in stdout and in a log file

## Quick Start

```bash
# Install the package
pip install -e .

# Run from config
env-setup-agent-from-config demo/new-example/configs/alice-biometrics_petisco__9abf7b1f6ef8c55bdddcb9a5c2eff513f6a93130/env-setup-agent-config.yaml
```

## YAML Configuration Format

Create a YAML config file with the following structure:

```yaml
# Repository information
repository:
  env_id: "alice-biometrics_petisco__9abf7b1f6ef8c55bdddcb9a5c2eff513f6a93130"
  repo_name: "alice-biometrics/petisco"
  commit_sha: "9abf7b1f6ef8c55bdddcb9a5c2eff513f6a93130"
  commit_date: "2024-01-15T12:00:00Z"

  # Paths (relative to repo root or absolute)
  repo_path: "demo/new-example/repos/alice-biometrics_petisco__9abf7b1f6ef8c55bdddcb9a5c2eff513f6a93130"
  env_dir: "demo/new-example/envs/alice-biometrics_petisco__9abf7b1f6ef8c55bdddcb9a5c2eff513f6a93130"

# Agent configuration
agent:
  model: null  # Use default or specify "claude-sonnet-4"
  max_rounds: 3
  build_timeout_s: 1800
  run_timeout_s: 1800

# Path configuration
paths:
  data_root: ""
  prompts_dir: "src/env_setup_agent/agent/prompts"
  templates_dir: "src/env_setup_agent/templating"
```

### Required Fields

Under `repository`:
- `env_id`: Unique identifier for this environment
- `repo_name`: Repository name (org/repo format)
- `commit_sha`: Git commit SHA
- `commit_date`: Commit date in ISO format (YYYY-MM-DDTHH:MM:SSZ)

### Optional Fields

Under `repository`:
- `repo_path`: Path to cloned repository (default: `repos/<env_id>`)
- `env_dir`: Output directory (default: `envs/<env_id>`)

Under `agent`:
- `model`: Claude model name (default: uses SDK default)
- `max_rounds`: Maximum iteration rounds (default: 3)
- `build_timeout_s`: Docker build timeout (default: 1800)
- `run_timeout_s`: Docker run timeout (default: 1800)

Under `paths`:
- `data_root`: Data root directory (default: "data")
- `prompts_dir`: Prompts directory (default: "src/env_setup_agent/agent/prompts")
- `templates_dir`: Templates directory (default: "src/env_setup_agent/templating")

## Path Resolution

All paths in the config can be:
1. **Absolute paths**: Used as-is
2. **Relative paths**: Resolved relative to repository root

The repository root is auto-detected by:
1. Looking for `.git` directory in parent directories
2. Falling back to the config file's directory

You can override this with `--repo-root`:

```bash
env-setup-agent-from-config config.yaml --repo-root /path/to/repo
```

## Logging

The agent logs to both:
1. **stdout**: Real-time console output
2. **Log file**: `<env_dir>/agent.log`

Log format:
```
2025-01-15 12:34:56 - env_setup_agent - INFO - Starting environment setup for alice-biometrics/petisco @ 9abf7b1...
2025-01-15 12:34:57 - env_setup_agent - INFO - Environment ID: alice-biometrics_petisco__9abf7b1...
2025-01-15 12:34:58 - env_setup_agent - INFO - Python cap: 3.12
```

## Output Structure

After running, the output directory will contain:

```
demo/new-example/envs/alice-biometrics_petisco__9abf7b1.../
├── Dockerfile              # Generated Dockerfile
├── run_instructions.sh     # Script to build and run tests
├── decision.json           # Agent's decision in JSON
├── summary.md              # Human-readable summary
├── agent.log               # Complete log file
└── _SUCCESS or _FAILURE    # Status marker
```

## Example Usage

### 1. Basic Usage

```bash
env-setup-agent-from-config demo/new-example/configs/alice-biometrics_petisco__9abf7b1f6ef8c55bdddcb9a5c2eff513f6a93130/env-setup-agent-config.yaml
```

### 2. With Custom Repo Root

```bash
env-setup-agent-from-config \
  demo/new-example/configs/alice-biometrics_petisco__9abf7b1f6ef8c55bdddcb9a5c2eff513f6a93130/env-setup-agent-config.yaml \
  --repo-root /path/to/eval_env_setup
```

### 3. From Python

```python
import asyncio
from pathlib import Path
from env_setup_agent.run_from_config import run_from_config

config_path = Path("demo/new-example/configs/.../env-setup-agent-config.yaml")
exit_code = asyncio.run(run_from_config(config_path))
```

## Directory Layout Example

Recommended structure for your project:

```
eval_env_setup/                     # Repository root
├── src/
│   └── env_setup_agent/            # Agent source code
│       ├── agent/
│       │   └── prompts/            # Prompt templates
│       └── templating/             # Dockerfile template
├── demo/
│   └── new-example/
│       ├── configs/
│       │   └── alice-biometrics_petisco__9abf7b1.../
│       │       └── env-setup-agent-config.yaml
│       ├── repos/
│       │   └── alice-biometrics_petisco__9abf7b1.../  # Cloned repo
│       └── envs/
│           └── alice-biometrics_petisco__9abf7b1.../  # Generated output
└── .git/
```

## Troubleshooting

### Config file not found

```bash
Error: Config file not found: /path/to/config.yaml
```

Make sure the path to your config file is correct.

### Repository path not found

```
2025-01-15 12:34:56 - env_setup_agent - ERROR - Repository path not found: /path/to/repo
```

Check that `repository.repo_path` in your config points to an existing directory with the cloned repository.

### Prompts or templates not found

Ensure your `paths.prompts_dir` and `paths.templates_dir` point to the correct locations. If using relative paths, they should be relative to the repository root.

### Viewing the log file

```bash
# Check the log file in the output directory
cat demo/new-example/envs/alice-biometrics_petisco__9abf7b1.../agent.log
```

## Advanced: Programmatic Usage

```python
import asyncio
import yaml
from pathlib import Path
from env_setup_agent.config import load_from_yaml
from env_setup_agent.runflow import run_one
from env_setup_agent.utils.logging import setup_logging

async def custom_run():
    config_path = Path("config.yaml")
    repo_root = Path.cwd()

    # Setup logging first
    log_file = Path("output/agent.log")
    setup_logging(log_file=log_file)

    # Load config
    config = load_from_yaml(config_path, repo_root)

    # Create RepoSpec (you'll need to extract this from your config)
    # ... then call run_one()

asyncio.run(custom_run())
```

## Environment Variables

You can still use environment variables to override config:

```bash
export ESA_MODEL="claude-sonnet-4"
export ESA_MAX_ROUNDS=5

env-setup-agent-from-config config.yaml
```

Config file values take precedence over environment variables.

## Benefits

1. **Version control**: Config files can be committed to git
2. **Reproducibility**: Same config produces same setup
3. **Flexibility**: Easy to test different configurations
4. **Debugging**: Complete logs in both console and file
5. **Custom paths**: Output wherever you want

## Migration from CLI

Old way:
```bash
env-setup-agent generate \
  alice-biometrics_petisco__9abf7b1 \
  alice-biometrics/petisco \
  9abf7b1f6ef8c55bdddcb9a5c2eff513f6a93130 \
  2024-01-15T12:00:00Z \
  --data-root demo/new-example
```

New way:
```bash
env-setup-agent-from-config \
  demo/new-example/configs/alice-biometrics_petisco__9abf7b1.../env-setup-agent-config.yaml
```
