## Policy

- Proceed only if tests can run with: a Python interpreter, Python dependencies, system libraries, and a direct pytest invocation.
- Proceed if the Docker image builds and the container executes the test command successfully, even when pytest returns a non-zero exit status due to failing tests. Refuse only for environment/setup failures (build errors, dependency install/runtime errors, policy violations).
- Refuse if one of the following holds:
  - no unit tests are present;
  - all unit tests are skipped;
  - external long-running services are required and the tests do not self-spawn/manage them and are not skipped/mocked.
    Presence of external-service configs (e.g., `docker-compose.yml`) by itself is not grounds to refuse; refuse only if those services are actually required for the test run and can not be skipped or mocked.
    If you refuse for this reason, always make sure the test involving external tests cannot be skipped or mocked by installing certain packages or setting certain environment variables.
- Install packages into the container’s base environment (no virtualenv inside the container).
- No services are started in the Dockerfile.
- Image base: `python:X.Y-slim` with `X.Y` <= the detected upper bound. The upper bound provided to you is inferred from the timestamp of the repo’s commit; choose the highest available **patch** within that minor.
- If a test is skipped, ignore its content when deciding to proceed/refuse. (A skipped test that would otherwise violate policy does not force refusal.)
  - However, if **all** tests are skipped, refuse to generate.
- Prefer installing from repository requirements files (e.g., `pip install -r requirements.txt`) over listing individual packages. Only pin direct packages when needed to resolve conflicts; justify such choices in evidence.
- Never include `-e .` in `pip_deps`. If an editable install is required, set `install_editable: true` and provide `pip_loc_e_dep` (e.g., `".[test]"`), which will be installed at **runtime** in `run.sh` (not during image build).
- Monorepos: proceed only if a **single** `test_worksubdir` yields a coherent unit-test run. Refuse when multiple subtrees require incompatible Python/dependency sets that cannot be satisfied by one environment.
- Always install the most comprehensive dependencies (unless conflicts exist), since running unit tests usually requires more dependencies than simply using the codebase.

### Additional Context: Proceed & Refuse Examples (with minimal guidance)

Below are compact, realistic examples to anchor output quality, plus small snippets to show how fields are used. Do **not** copy versions/paths blindly—adapt to the current repo and commit.

PROCEED — JSON example
{
  "status": "proceed",
  "reason": "",
  "evidence": {
    "tests_exist": [
      "tests/test_api.py contains pytest tests",
      "pytest.ini found at project root"
    ],
    "python_version_constraints": [
      ".github/workflows/ci.yml matrix includes 3.10, 3.11"
    ],
    "dependency_manifests": [
      "requirements.txt",
      "requirements-dev.txt"
    ],
    "service_notes": [
      "docker-compose.yml present but integration tests are skipped",
      "unit tests use sqlite in-memory"
    ]
  },
  "variables": {
    "python_version_tag": "3.11.13-slim",
    "test_worksubdir": ".",
    "project_apt_packages": ["gcc", "libffi-dev", "libssl-dev"],
    "env_vars": {
      "DATABASE_URL": "sqlite:///test.db",
      "PYTHONUNBUFFERED": "1"
    },
    "pip_deps": ["-r requirements.txt", "-r requirements-dev.txt"],
    "install_editable": true,
    "pip_loc_e_dep": ".[test]",
    "test_cmd": ["pytest", "-q"]
  }
}

REFUSE — JSON example
{
  "status": "refuse",
  "reason": "no unit tests detected; integration suite requires external services (postgres, redis) with no mocks; tests not skipped",
  "evidence": {
    "tests_exist": [
      "no files matching 'tests/**/test_*.py' or '*_test.py'"
    ],
    "external_services": [
      "docker-compose.yml brings up postgres and redis",
      "pytest.ini: addopts includes -m 'integration' with no skip markers"
    ]
  }
}

Your generated variables will be used to render the following jinja2 templates to build env and run test. Variables not mentioned in the contract json are provided by an input config you don't need to know.

Dockerfile jinja2 template

```Dockerfile
# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION={{ python_version_tag }}
FROM python:${PYTHON_VERSION}

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Project-level env vars

{% for k, v in env_vars.items() -%}
ENV {{ k }}="{{ v }}"
{% endfor %}

# Base system packages + project APT

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      build-essential pkg-config git ca-certificates{% if project_apt_packages and project_apt_packages|length > 0 %} \
      {{ project_apt_packages | join(' ') }}{% endif %} \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps from repo without copying (BuildKit bind mount)

{% for arg in pip_deps -%}
RUN --mount=type=bind,source=.,target={{ mount_dir }},ro \
    --mount=type=cache,target=/root/.cache/pip \
    pip install {{ arg }}
{% endfor %}

# Non-root user and working directory where tests run

RUN useradd -m -s /bin/bash {{ app_user }} \
 && mkdir -p {{ mount_dir }} \
 && chown -R {{ app_user }}:{{ app_user }} {{ mount_dir }}
USER {{ app_user }}

WORKDIR {{ test_workdir }}
```

build.sh jinja2 template

```bash
# !/usr/bin/env bash

set -euo pipefail

ENV_DIR="{{ env_dir }}"
IMAGE_TAG="{{ image_tag }}"
REPO_PATH="{{ repo_path }}"

docker build -f "$ENV_DIR/Dockerfile" -t "$IMAGE_TAG" "$REPO_PATH"
```

run.sh jinja2 template

```bash
# !/usr/bin/env bash

set -euo pipefail

REPO_PATH="{{ repo_path }}"
MOUNT_DIR="{{ mount_dir }}"
IMAGE_TAG="{{ image_tag }}"
TEST_WORKDIR="{{ test_workdir }}"

docker run --rm \
  -v "$REPO_PATH":"$MOUNT_DIR" \
  --user "$(id -u):$(id -g)" \
  "$IMAGE_TAG" \
  bash -lc "{% if install_editable %}pip install -e '{{ pip_loc_e_dep }}' && {% endif %}cd '{{ TEST_WORKDIR }}' && {{ test_cmd }}"
```

Evidence format tips:

- Prefer path + precise anchor: `path:line` or a short quoted snippet showing the key marker (e.g., `envlist = py311`).
- tests_exist: `tests/test_*.py`, `src/pkg/tests/...`, `pytest.ini present`
- python_version_constraints: `tox.ini: envlist=py311`, `CI matrix: 3.10, 3.11`
- dependency_manifests: `requirements*.txt`, `pyproject.toml [project.optional-dependencies].test`
- external_services (if any): `docker-compose.yml: postgres`; note if those tests are skipped/mocked

Non-obvious guardrails (beyond the schema):

- Use the highest patch for `python_version_tag` within the provided cap (major.minor).
- `test_worksubdir` is relative (e.g., ".", "backend"); choose the smallest subdir that contains and runs the unit tests.
- Prefer requirements files in `pip_deps`; ensure referenced files exist. Add direct packages only if necessary and justify.
- Keep `project_apt_packages` minimal and justified by Python deps (e.g., psycopg2 → libpq-dev; lxml → libxml2-dev libxslt1-dev).
- `test_cmd` is argv only (no shell operators). Editable install happens at runtime before `test_cmd` executes, not during image build.
