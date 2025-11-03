# env_setup_agent — Design Document

## Background

We want a **reproducible, automatic way** to generate a Dockerfile for an arbitrary Python repository so that, after building the image, we can mount the repo and run `pytest` inside the container. We’ll use an AI agent to:

1. scan the repo (read-only),
2. propose **template variables** for a fixed Dockerfile Jinja2 template,
3. iterate (fix → rebuild → rerun tests) until we either succeed, refuse, or hit limits.

We’ll implement the agent with **Claude Agent SDK (Python)**, which supports both single-shot calls and stateful sessions and can use built-in read-only tools (e.g., Read, Glob, Grep) with a configurable permission model and a working directory. ([Claude Docs][1])

---

## High-level design

### Core ideas

* **Template, not freeform**: we never let the model write a raw Dockerfile. The model only returns **validated JSON variables** for our Jinja2 template.
* **Read-only repo access**: the model can **read** files to decide versions, dependencies, and test presence; it **cannot** modify files.
* **BuildKit during build, no COPY**: at build time we **bind-mount** the repo into a `RUN` step to `pip install` everything (optionally `-e .`) without embedding code into layers. Runtime uses the **same mount path** so editable installs resolve.
* **Iterative loop**: (generate → build → run tests → feed logs back → revise) with hard caps on rounds/time.
* **Deterministic outputs**: success writes `Dockerfile`, `run_instructions.sh`, `_SUCCESS`, and `summary.md`; refusal writes `_FAILURE` and `summary.md` with an enum reason.

### What env_setup_agent does

1. **Scans** a repo to gather facts (tests present, Python version constraints, dependency manifests, likely system libs, external-service indicators, etc.).
2. **Asks Claude** (read-only) for variables to fill the template.
3. **Renders** the Jinja2 Dockerfile.
4. **Builds** the image using BuildKit (bind-mounting the repo inside a `RUN`).
5. **Runs** `pytest` in the container with the repo mounted to the same path.
6. **Classifies** results (ok / pytest failures / dependency errors / build failure) and either **finishes** or **iterates** with build/run logs.
7. **Emits artifacts** under `data/` (Dockerfile, scripts, logs, prompt, summary, success/failure marker).

---

## Structural design

```
env_setup_agent/
├── pyproject.toml
├── README.md
├── src/
│   └── env_setup_agent/
│       ├── __init__.py
│       ├── cli.py                     # CLI entrypoints (scan, generate, build, test, all)
│       ├── runflow.py                 # high-level controller (no “pipeline” wording)
│       ├── config/
│       │   ├── model.py               # config dataclasses & defaults
│       │   └── load.py                # load/merge config (file + env + CLI)
│       ├── core/
│       │   ├── enums.py               # Status & FailureReason enums
│       │   ├── models.py              # RepoSpec, Facts, DockerVars, Decision, BuildResult, TestResult
│       │   ├── schema.py              # JSON schema & validator for agent output
│       │   ├── summarize.py           # write summary.md and markers
│       │   └── paths.py               # data/* path helpers
│       ├── detect/
│       │   ├── tests_detector.py      # find tests/… or CI pytest usage
│       │   ├── python_version.py      # infer constraints; merge with commit-date cap
│       │   ├── dep_files.py           # requirements*, pyproject, setup.*, Pipfile
│       │   ├── sys_pkgs.py            # infer apt libs from python deps
│       │   ├── services.py            # external-service indicators
│       │   └── facts.py               # aggregate Facts
│       ├── agent/
│       │   ├── claude_runner.py       # session, prompts, iteration loop (read-only tools)
│       │   ├── prompts/
│       │   │   ├── system.md          # role + output rules
│       │   │   ├── policy.md          # refusal & constraints
│       │   │   ├── contract.json      # JSON contract (schema)
│       │   │   ├── repo_task.md.j2    # initial task prompt (templated)
│       │   │   └── iterate.md.j2      # iteration prompt for feeding logs
│       ├── templating/
│       │   ├── jinja_env.py           # Jinja setup
│       │   └── dockerfile.template.j2 # BuildKit + bind-mount install
│       ├── docker/
│       │   ├── build.py               # docker build (BuildKit), capture logs
│       │   ├── run.py                 # docker run pytest, capture logs
│       │   ├── classify.py            # classify run outcome
│       │   └── instructions.py        # write run_instructions.sh
│       ├── io/
│       │   ├── fs.py                  # atomic writes, mkdirs
│       │   ├── logs.py                # simple JSONL logging
│       │   ├── repo_index.py          # iterate data/repos/*
│       │   └── yaml_io.py             # per-repo overrides (optional)
│       └── adapters/
│           ├── github_commit.py       # wraps your CommitInfoFetcher (upper bound by date)
│           └── clock.py               # timestamps
└── tests/
```

---

## Low-level design (code & prompts)

> The code below is **ready-to-adapt** (imports, types, control flow). Omit or expand as needed.

### `core/enums.py`

```python
from enum import Enum

class Status(str, Enum):
    PROCEED = "proceed"
    REFUSE = "refuse"

class FailureReason(str, Enum):
    NO_TESTS_FOUND = "no_tests_found"
    EXTERNAL_SERVICE_REQUIRED = "external_service_required"
    BUILD_FAILED = "build_failed"
    DEPENDENCY_INSTALL_FAILED = "dependency_install_failed"
    RUNTIME_DEPENDENCY_ERROR = "runtime_dependency_error"
    DOCKER_TIMEOUT = "docker_timeout"
    INVALID_AGENT_OUTPUT = "invalid_agent_output"
    POLICY_VIOLATION = "policy_violation"
    OTHER = "other"
```

### `core/models.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from .enums import Status, FailureReason

@dataclass
class RepoSpec:
    env_id: str
    repo_name: str        # org/repo
    commit_sha: str
    commit_ts_iso: str
    repo_path: str        # data/repos/<env_id>
    env_dir: str          # data/envs/<env_id>

@dataclass
class Facts:
    tests_found: List[str]
    python_constraints: List[str]
    python_cap_minor: Tuple[int, int]
    dep_manifests: List[str]
    pip_plan: List[str]
    sys_packages: List[str]
    service_indicators: List[str]
    test_subdir: str
    allow_editable: bool

@dataclass
class DockerVars:
    python_version_tag: str
    mount_dir: str
    repo_bind_src: str
    test_workdir: str
    app_user: str
    project_apt_packages: List[str]
    env_vars: Dict[str, str]
    pip_deps: List[str]
    install_editable: bool
    test_cmd: List[str]

@dataclass
class Decision:
    status: Status
    reason: Optional[str]
    variables: Optional[DockerVars]
    evidence: Dict[str, List[str]] = field(default_factory=dict)

@dataclass
class BuildResult:
    success: bool
    image_tag: str
    log_path: str
    failure_reason: Optional[FailureReason] = None
    message: str = ""

@dataclass
class TestResult:
    status: str             # "ok" | "pytest_failed" | "deps_error" | "build_failed"
    returncode: int
    log_path: str
    failure_reason: Optional[FailureReason] = None
    message: str = ""
```

### `core/schema.py` (JSON schema for agent output)

```python
import json
from jsonschema import Draft202012Validator

SCHEMA = {
  "type": "object",
  "required": ["status"],
  "properties": {
    "status": {"enum": ["proceed", "refuse"]},
    "reason": {"type": "string"},
    "evidence": {"type": "object",
      "additionalProperties": {"type": "array", "items": {"type": "string"}}
    },
    "variables": {
      "type": "object",
      "required": ["python_version_tag","mount_dir","repo_bind_src","test_workdir",
                   "app_user","project_apt_packages","env_vars","pip_deps",
                   "install_editable","test_cmd"],
      "properties": {
        "python_version_tag": {"type":"string","pattern":"^\\d+\\.\\d+\\.\\d+-slim$"},
        "mount_dir": {"type":"string"},
        "repo_bind_src": {"type":"string"},
        "test_workdir": {"type":"string"},
        "app_user": {"type":"string"},
        "project_apt_packages": {"type":"array","items":{"type":"string"}},
        "env_vars": {"type":"object","additionalProperties":{"type":"string"}},
        "pip_deps": {"type":"array","items":{"type":"string"}},
        "install_editable": {"type":"boolean"},
        "test_cmd": {"type":"array","items":{"type":"string"}}
      },
      "additionalProperties": False
    }
  },
  "allOf":[
    {"if":{"properties":{"status":{"const":"proceed"}}},"then":{"required":["variables"]}},
    {"if":{"properties":{"status":{"const":"refuse"}}},"then":{"required":["reason"]}}
  ],
  "additionalProperties": False
}

VALIDATOR = Draft202012Validator(SCHEMA)

def validate_or_error(obj: dict) -> str | None:
    errs = sorted(VALIDATOR.iter_errors(obj), key=lambda e: e.path)
    return None if not errs else "\n".join(f"- {e.message}" for e in errs)
```

### `templating/dockerfile.template.j2`

```dockerfile
# syntax=docker/dockerfile:1.7
{# REQUIRED:
   python_version_tag, mount_dir, repo_bind_src, test_workdir,
   app_user, project_apt_packages, env_vars, pip_deps,
   install_editable, test_cmd
#}

ARG PYTHON_VERSION={{ python_version_tag }}
FROM python:${PYTHON_VERSION}

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8
{%- for k, v in env_vars.items() %}
ENV {{ k }}="{{ v }}"
{%- endfor %}

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      build-essential pkg-config git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

{%- if project_apt_packages and project_apt_packages|length > 0 %}
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
{%- for p in project_apt_packages %}
      {{ p }} \
{%- endfor %}
    && rm -rf /var/lib/apt/lists/*
{%- endif %}

ARG APP_USER={{ app_user }}
RUN useradd -m ${APP_USER} && mkdir -p {{ mount_dir }} && chown -R ${APP_USER}:${APP_USER} {{ mount_dir }}
USER ${APP_USER}
ENV XDG_CACHE_HOME=/home/${APP_USER}/.cache

RUN --mount=type=cache,target=/home/${APP_USER}/.cache/pip \
    --mount=type=bind,source={{ repo_bind_src }},target={{ mount_dir }},rw \
    bash -lc 'set -euo pipefail; \
      cd "{{ test_workdir }}"; \
      python -m pip install --upgrade pip; \
{%- for step in pip_deps %}
      echo "+ pip install {{ step }}"; pip install {{ step }}; \
{%- endfor %}
{%- if install_editable %}
      echo "+ pip install -e ."; pip install -e .; \
{%- endif %}
      true'

WORKDIR {{ test_workdir }}
{%- set _cmd = (test_cmd | default(["python","-m","pytest"])) %}
CMD {{ _cmd | tojson }}
```

### `agent/prompts/system.md`

```
You are EnvSetupAgent. Your job is to output ONLY a single JSON object that conforms to the provided contract.
You may read repository files with the provided tools. Do not write or execute code. Do not output commentary.
```

### `agent/prompts/policy.md`

```
POLICY
- Proceed only if tests can run with: Python interpreter, Python deps, system libs, and direct pytest.
- Refuse if: no tests; or external long-running services are required unless tests self-spawn/manage them.
- No virtualenvs in Dockerfile. No services started in Dockerfile.
- Base: python:X.Y-slim with X.Y <= the detected upper bound.
```

### `agent/prompts/contract.json`

```json
{
  "type": "object",
  "required": ["status"],
  "properties": {
    "status": { "enum": ["proceed", "refuse"] },
    "reason": { "type": "string" },
    "evidence": { "type": "object", "additionalProperties": { "type": "array", "items": { "type": "string" } } },
    "variables": {
      "type": "object",
      "required": [
        "python_version_tag","mount_dir","repo_bind_src","test_workdir",
        "app_user","project_apt_packages","env_vars","pip_deps",
        "install_editable","test_cmd"
      ],
      "properties": {
        "python_version_tag": { "type":"string","pattern":"^\\d+\\.\\d+\\.\\d+-slim$" },
        "mount_dir": { "type":"string" },
        "repo_bind_src": { "type":"string" },
        "test_workdir": { "type":"string" },
        "app_user": { "type":"string" },
        "project_apt_packages": { "type":"array","items":{"type":"string"} },
        "env_vars": { "type":"object","additionalProperties":{"type":"string"} },
        "pip_deps": { "type":"array","items":{"type":"string"} },
        "install_editable": { "type":"boolean" },
        "test_cmd": { "type":"array","items":{"type":"string"} }
      },
      "additionalProperties": false
    }
  },
  "allOf": [
    { "if": { "properties": { "status": { "const": "proceed" } } }, "then": { "required": ["variables"] } },
    { "if": { "properties": { "status": { "const": "refuse" } } }, "then": { "required": ["reason"] } }
  ],
  "additionalProperties": false
}
```

### `agent/prompts/repo_task.md.j2`

```
TASK
Scan the repository read-only and produce variables for a Dockerfile that installs all Python dependencies
at build time using Docker BuildKit bind mounts (no COPY), then runs pytest as CMD.

CONTEXT
- Repo: {{ repo_name }}
- Commit: {{ commit_sha }}
- Python minor cap: {{ python_cap_minor[0] }}.{{ python_cap_minor[1] }} (choose highest patch in this minor or lower)

CHECKS
- Confirm tests exist (tests/ or CI pytest).
- Gather python version constraints (files in priority order).
- Detect dependency manifests and infer APT libs (e.g., libssl-dev, libffi-dev, libxml2-dev, libxslt1-dev, gfortran, libopenblas-dev).
- Flag external-service requirements (compose, GH Actions services, Testcontainers, unmocked DATABASE_URL, etc.).

OUTPUT
Return ONLY the JSON object per the contract. Do not add prose.
```

### `agent/prompts/iterate.md.j2`

````
PREVIOUS VARIABLES
```json
{{ previous_vars_json }}
````

UPDATE (build/run logs, tails)
=== BUILD LOG ===
{{ build_log_tail }}

=== RUN LOG ===
{{ run_log_tail }}

Return ONLY the revised JSON per the same contract. If policy is violated, set status="refuse" with reason & evidence.

````

### `agent/claude_runner.py` (session + iteration)

```python
import asyncio, json, textwrap
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock
# Docs: Python SDK supports single-call query and stateful client; options include system_prompt, allowed_tools, cwd, permission settings. :contentReference[oaicite:1]{index=1}

from ..core.models import Decision, DockerVars
from ..core.enums import Status, FailureReason
from ..core import schema as schema_mod

# ------------- utilities -------------

def first_json_object(s: str) -> Dict[str, Any]:
    start = s.find("{")
    if start == -1:
        raise ValueError("no json")
    for end in range(len(s), start, -1):
        try:
            return json.loads(s[start:end])
        except json.JSONDecodeError:
            continue
    raise ValueError("no valid json")

def map_decision(obj: Dict[str, Any]) -> Decision:
    err = schema_mod.validate_or_error(obj)
    if err:
        return Decision(Status.REFUSE, f"invalid output: {err}", None, {})
    status = Status(obj["status"])
    variables = None
    if status is Status.PROCEED:
        v = obj["variables"]
        variables = DockerVars(
            python_version_tag=v["python_version_tag"],
            mount_dir=v["mount_dir"],
            repo_bind_src=v["repo_bind_src"],
            test_workdir=v["test_workdir"],
            app_user=v["app_user"],
            project_apt_packages=v.get("project_apt_packages", []),
            env_vars=v.get("env_vars", {}),
            pip_deps=v.get("pip_deps", []),
            install_editable=bool(v.get("install_editable", False)),
            test_cmd=v.get("test_cmd", ["python","-m","pytest"])
        )
    return Decision(status, obj.get("reason"), variables, obj.get("evidence", {}))

# ------------- prompts -------------

def system_prompt() -> str:
    return "You are EnvSetupAgent. Output ONLY a single JSON object that matches the provided contract. Read-only access."

def assemble_initial_user(repo_task: str, policy: str, contract_json: str) -> str:
    return "\n\n".join([repo_task, "POLICY", policy, "CONTRACT", f"```json\n{contract_json}\n```", "Return only the JSON."])

def assemble_iteration_user(prev_vars: DockerVars, build_tail: str, run_tail: str) -> str:
    prev_json = json.dumps(asdict(prev_vars), indent=2)
    body = textwrap.dedent(f"""
    PREVIOUS VARIABLES
    ```json
    {prev_json}
    ```

    === BUILD LOG (tail) ===
    {build_tail}

    === RUN LOG (tail) ===
    {run_tail}

    Return only the JSON per the same contract.
    """)
    return body

# ------------- agent loop -------------

class ClaudeRepoAgent:
    def __init__(self, repo_path: Path, model: Optional[str] = None):
        self.repo_path = Path(repo_path).resolve()
        self.options = ClaudeAgentOptions(
            system_prompt=system_prompt(),
            allowed_tools=["Glob","Grep","Read"],  # read-only
            permission_mode="denyEdits",           # forbid writes/exec
            cwd=str(self.repo_path),
            model=model
        )

    async def _ask(self, client: ClaudeSDKClient, user_text: str) -> Decision:
        await client.query(user_text)
        chunks: List[str] = []
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for blk in msg.content:
                    if isinstance(blk, TextBlock):
                        chunks.append(blk.text)
        try:
            raw = first_json_object("".join(chunks))
        except Exception as e:
            return Decision(Status.REFUSE, f"invalid output: {e}", None, {})
        return map_decision(raw)

    async def run(
        self,
        repo_name: str,
        commit_sha: str,
        py_cap_minor: Tuple[int,int],
        build_and_test_cb,     # (DockerVars)-> (ok,boolLogTail,str,str,class)
        max_rounds: int = 3,
        task_tpl: str = "",
        policy_txt: str = "",
        contract_json: str = ""
    ) -> Decision:
        # initial prompt
        repo_task = task_tpl.format(
            repo_name=repo_name, commit_sha=commit_sha,
            python_cap=f"{py_cap_minor[0]}.{py_cap_minor[1]}"
        )
        user0 = assemble_initial_user(repo_task, policy_txt, contract_json)

        async with ClaudeSDKClient(options=self.options) as client:
            decision = await self._ask(client, user0)
            if decision.status is Status.REFUSE:
                return decision

            rounds = 1
            while rounds <= max_rounds:
                assert decision.variables
                ok, build_tail, run_tail, classification = await build_and_test_cb(decision.variables)

                if ok or classification == "pytest_failed":
                    return decision

                user_iter = assemble_iteration_user(decision.variables, build_tail[-32000:], run_tail[-32000:])
                decision = await self._ask(client, user_iter)
                if decision.status is Status.REFUSE:
                    return decision
                rounds += 1

            return Decision(Status.REFUSE, f"max rounds {max_rounds} reached", None, {"loop":["max_rounds_exhausted"]})
````

> The SDK supports both one-shot `query()` and stateful `ClaudeSDKClient` sessions with options like `system_prompt`, `cwd`, `allowed_tools`, and permission settings. That enables exactly our read-only scan with iteration pattern. ([Claude Docs][1])

### `docker/build.py`

```python
import os, subprocess, shlex
from pathlib import Path
from ..core.enums import FailureReason
from ..core.models import BuildResult

def docker_build(env_dir: Path, image_tag: str, data_root: Path, timeout_s: int = 1800) -> BuildResult:
    dockerfile = env_dir / "Dockerfile"
    log_path = env_dir.parent.parent / "trajectories" / env_dir.name / "build.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = f"docker build -f {shlex.quote(str(dockerfile))} -t {shlex.quote(image_tag)} {shlex.quote(str(data_root))}"
    env = os.environ.copy()
    env["DOCKER_BUILDKIT"] = "1"

    with log_path.open("w") as logf:
        proc = subprocess.Popen(cmd, shell=True, stdout=logf, stderr=subprocess.STDOUT, env=env)
        try:
            rc = proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            return BuildResult(False, image_tag, str(log_path), FailureReason.DOCKER_TIMEOUT, "build timeout")
    if rc != 0:
        return BuildResult(False, image_tag, str(log_path), FailureReason.BUILD_FAILED, "docker build failed")
    return BuildResult(True, image_tag, str(log_path))
```

### `docker/run.py` & `docker/classify.py`

```python
# run.py
import os, subprocess, shlex
from pathlib import Path

def docker_run(image_tag: str, repo_path: Path, mount_dir: str, env_dir: Path, timeout_s: int = 1800):
    log_path = env_dir.parent.parent / "trajectories" / env_dir.name / "run.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "docker","run","--rm",
        "-v", f"{repo_path}:{mount_dir}",
        "--user", f"{os.getuid()}:{os.getgid()}",
        image_tag
    ]
    with log_path.open("w") as logf:
        proc = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT)
        try:
            rc = proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            return rc, str(log_path), "timeout"
    return rc, str(log_path), "ok"

# classify.py
def classify_run_returncode(rc: int, log_tail: str) -> str:
    if rc == 0:
        return "ok"
    if "ModuleNotFoundError" in log_tail or "ImportError" in log_tail:
        return "deps_error"
    if "No matching distribution found" in log_tail or "ResolutionImpossible" in log_tail:
        return "deps_error"
    return "pytest_failed"
```

### `templating/jinja_env.py`

```python
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pathlib import Path

def make_env(templates_dir: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
```

### `runflow.py` (controller)

```python
import asyncio, json
from pathlib import Path
from .core.models import RepoSpec, Decision
from .core.enums import Status, FailureReason
from .templating.jinja_env import make_env
from .docker.build import docker_build
from .docker.run import docker_run
from .docker.classify import classify_run_returncode
from .agent.claude_runner import ClaudeRepoAgent
from .core.summarize import write_summary

def render_dockerfile(env_dir: Path, templates_dir: Path, vars_dict: dict):
    env = make_env(templates_dir)
    tpl = env.get_template("dockerfile.template.j2")
    dockerfile = tpl.render(**vars_dict)
    out_path = env_dir / "Dockerfile"
    env_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(dockerfile)

def write_run_instructions(env_dir: Path, image_tag: str, data_root: Path, mount_dir: str, env_id: str):
    sh = f"""#!/usr/bin/env bash
set -euo pipefail
export DOCKER_BUILDKIT=1
docker build -f data/envs/{env_id}/Dockerfile -t {image_tag} data/
docker run --rm -v "$PWD/data/repos/{env_id}":"{mount_dir}" --user "$(id -u):$(id -g)" {image_tag}
"""
    p = env_dir / "run_instructions.sh"
    p.write_text(sh)
    p.chmod(0o755)

async def run_one(
    spec: RepoSpec,
    python_cap_minor: tuple[int,int],
    prompts_dir: Path,
    templates_dir: Path,
    data_root: Path,
    model: str | None = None,
    max_rounds: int = 3
) -> Decision:
    # Load prompt fragments
    system = (prompts_dir/"system.md").read_text()
    policy = (prompts_dir/"policy.md").read_text()
    contract = (prompts_dir/"contract.json").read_text()
    repo_task_tpl = (prompts_dir/"repo_task.md.j2").read_text()

    # Agent
    agent = ClaudeRepoAgent(repo_path=Path(spec.repo_path), model=model)
    async def build_and_test_cb(dvars):
        # render dockerfile
        render_dockerfile(Path(spec.env_dir), templates_dir, vars(dvars))
        # build
        tag = f"envsetup/{spec.env_id}:tests"
        bres = docker_build(Path(spec.env_dir), tag, data_root)
        build_tail = Path(bres.log_path).read_text()[-32000:] if Path(bres.log_path).exists() else ""
        if not bres.success:
            return (False, build_tail, "", "build_failed")
        # run
        rc, run_log_path, _ = docker_run(tag, Path(spec.repo_path), dvars.mount_dir, Path(spec.env_dir))
        run_tail = Path(run_log_path).read_text()[-32000:] if Path(run_log_path).exists() else ""
        cls = classify_run_returncode(rc, run_tail)
        ok = cls in ("ok","pytest_failed")
        return (ok, build_tail, run_tail, cls)

    decision = await agent.run(
        repo_name=spec.repo_name,
        commit_sha=spec.commit_sha,
        py_cap_minor=python_cap_minor,
        build_and_test_cb=build_and_test_cb,
        max_rounds=max_rounds,
        task_tpl=repo_task_tpl,
        policy_txt=policy,
        contract_json=contract
    )

    # Artifacts
    env_dir = Path(spec.env_dir)
    (env_dir / ("_SUCCESS" if decision.status is Status.PROCEED else "_FAILURE")).write_text("")
    write_run_instructions(env_dir, f"envsetup/{spec.env_id}:tests", data_root, decision.variables.mount_dir if decision.variables else "/workspace", spec.env_id)
    write_summary(env_dir, spec, decision)

    return decision
```

### `core/summarize.py`

```python
from pathlib import Path
from .models import RepoSpec, Decision
from .enums import Status

def write_summary(env_dir: Path, spec: RepoSpec, decision: Decision):
    p = env_dir / "summary.md"
    if decision.status is Status.PROCEED and decision.variables:
        v = decision.variables
        p.write_text(f"""# Generation Summary — Success
- Repo: {spec.repo_name} @ {spec.commit_sha}
- Python base: {v.python_version_tag}
- APT: {", ".join(v.project_apt_packages) or "(none)"}
- Pip plan: {", ".join(v.pip_deps) or "(none)"}
- Editable: {v.install_editable}
- Mount path: {v.mount_dir}
- Test workdir: {v.test_workdir}
""")
    else:
        p.write_text(f"""# Generation Summary — Refused
Reason: {decision.reason or "(unspecified)"}
Evidence:
{chr(10).join("- " + e for cat in decision.evidence for e in decision.evidence[cat])}
""")
```

---

## Constraints & assumptions

* **Docker BuildKit** required for `RUN --mount=type=bind` and `--mount=type=cache`. Enable via `DOCKER_BUILDKIT=1`.
* **Claude Agent SDK (Python)** and **Claude Code CLI** installed; we use **stateful sessions** with read-only tools and set the agent **cwd** to the repo path. (The SDK provides `query()` and `ClaudeSDKClient`, supports `system_prompt`, `cwd`, and allowed tool configuration.) ([Claude Docs][1])
* The agent is **read-only** (allowed tools: `Glob`, `Grep`, `Read`; permission mode denies edits).
* The repo is **already cloned** under `data/repos/<env_id>` and will be mounted to **the same path** at runtime as seen during build.
* We only target **Python 3** projects.
* External services are **not** allowed unless tests **self-spawn and manage** them; otherwise we **refuse**.

---

## Example: run on a single repo (step-by-step)

Assume this layout:

```
data/
├── repos/
│   └── reponame__deadbeef/        # cloned repo (already present)
└── envs/
    └── reponame__deadbeef/        # env outputs will be written here
```

1. **Install prerequisites**

```bash
pip install claude-agent-sdk jinja2 jsonschema
npm i -g @anthropic-ai/claude-code   # Claude Code CLI if not installed
export CLAUDE_API_KEY=...            # if required by your local setup
```

2. **Prepare prompts & template**
   Place prompt fragments and `dockerfile.template.j2` as shown in the structure.

3. **Run the controller** (from your own script or REPL)

```python
import asyncio
from pathlib import Path
from env_setup_agent.core.models import RepoSpec
from env_setup_agent.runflow import run_one

spec = RepoSpec(
    env_id="reponame__deadbeef",
    repo_name="org/reponame",
    commit_sha="deadbeef",
    commit_ts_iso="2024-01-01T00:00:00Z",
    repo_path="data/repos/reponame__deadbeef",
    env_dir="data/envs/reponame__deadbeef"
)
python_cap_minor = (3, 11)  # e.g., from your commit-date cap logic

asyncio.run(run_one(
    spec=spec,
    python_cap_minor=python_cap_minor,
    prompts_dir=Path("env_setup_agent/src/env_setup_agent/agent/prompts"),
    templates_dir=Path("env_setup_agent/src/env_setup_agent/templating"),
    data_root=Path("data"),
    model=None,
    max_rounds=3
))
```

4. **Inspect outputs**

```
data/envs/reponame__deadbeef/
├── Dockerfile
├── run_instructions.sh
├── _SUCCESS or _FAILURE
└── summary.md

data/trajectories/reponame__deadbeef/
├── build.log
└── run.log

data/prompts/reponame__deadbeef/
└── prompt.md (optional if you choose to persist)
```

5. **Manually run if desired**

```bash
cd data
export DOCKER_BUILDKIT=1
bash envs/reponame__deadbeef/run_instructions.sh
```

---

## Notes on Claude Agent SDK usage

* **Choosing interaction mode**: The Python SDK offers both `query()` (one-shot) and a stateful `ClaudeSDKClient`. We use the **session client** to iterate with logs and maintain context. ([Claude Docs][1])
* **Read-only tools & permissions**: We pass options to allow only `Read/Glob/Grep`, set `cwd` to the repo, and restrict permissions to **deny edits**, aligning with the SDK’s permission model guidance. ([Claude Docs][2])
* **Hosting/ops**: The SDK maintains conversational state and executes tool calls in a persistent environment; plan capacity accordingly if you run many repos concurrently. ([Claude Docs][3]). You should also be prepared for failure due to rate limiting, in which case you can simply abort the generation without saving any generated dockerfile or other data

---

## Why this design works

* **Safety & determinism**: model can only read; Dockerfile is always our template; output must validate against a schema.
* **Speed**: BuildKit cache + bind mounts install deps at build time without copying the repo; re-runs are fast.
* **Observability**: prompts, raw agent JSON, build logs, and summaries live under `data/`.
* **Extensibility**: add more detectors, refine apt inference, or plug in another provider by swapping the `agent/*` adapter.

[1]: https://docs.claude.com/en/api/agent-sdk/python?utm_source=chatgpt.com "Agent SDK reference - Python"
[2]: https://docs.claude.com/en/api/agent-sdk/overview?utm_source=chatgpt.com "Agent SDK overview"
[3]: https://docs.claude.com/en/api/agent-sdk/hosting?utm_source=chatgpt.com "Hosting the Agent SDK"
