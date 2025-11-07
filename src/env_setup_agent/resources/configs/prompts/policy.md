## Policy

- Proceed only if tests can run with: Python interpreter, Python deps, system libs, and direct pytest.
- Refuse if one of the following:
  - no unit tests;
  - all unit tests are skipped;
  - external long-running services are required, unless tests self-spawn/manage them, or tests involving external services are skipped.
    If the unit tests expect access to an external services like databases, message queues, GitHub Actions services, etc, refuse.
    However, if external services are detected but tests use mocking or self-contained test fixtures, you may proceed.
    Also, if some tests depending on external services are skipped, you may also proceed unless all tests are skipped.
- You should install directly in the docker's env, instead of in a virtial env running in docker.
- No services started in Dockerfile.
- Image base: `python:X.Y-slim` with X.Y <= the detected upper bound. The upper bound is inferred from the timestamp of the repo's last commit, so it's impossible for the chosen python interpreter to have a higher version.
- If a test is skipped, ignore it and don't refuse because of its content. This means, even if a skipped test violate any of the rule of a valid case (e.g. depending on external service), we won't refuse the generation because the test is skipped.
  - However, if all tests are skipped, refuse to generate.
- Always prefer install from requirements files provided in the repo (e.g. `pip install -r requirements.txt`) over manually specify the packages (e.g. `pip install numpy==2.3.0`). Use manual method only when there exists package conflicts, and you must manually resolve it (since you can't modify the provided repo).

### Additional Context: Proceed & Refuse Examples (with minimal guidance)

Below are compact, realistic examples to anchor output quality, plus small snippets to show how fields are used. Do **not** copy versions/paths blindly - adapt to the current repo and commit.

PROCEED — JSON example
{
  "status": "proceed",
  "reason": null,
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
  "reason": "no unit tests detected; only integration suite requires external services (postgres, redis) with no mocks; all tests marked 'integration' and not skipped",
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

Dockerfile (template extract, aligned to current vars)

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

build.sh (template extract)

# !/usr/bin/env bash

set -euo pipefail

ENV_DIR="{{ env_dir }}"
IMAGE_TAG="{{ image_tag }}"
REPO_PATH="{{ repo_path }}"

docker build -f "$ENV_DIR/Dockerfile" -t "$IMAGE_TAG" "$REPO_PATH"

run.sh (template extract)

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
  bash -lc '{% if install_editable %}pip install -e {{ pip_loc_e_dep }} && {% endif %}cd "{{ TEST_WORKDIR }}" && {{ test_cmd }}'

Evidence format tips (keep it short, file-first):

- tests_exist: "tests/test_*.py", "src/pkg/tests/…", "pytest.ini present"
- python_version_constraints: "tox.ini envlist=py311", "CI matrix: 3.10, 3.11"
- dependency_manifests: "requirements*.txt", "pyproject.toml [project.optional-dependencies].test"
- external_services (if any): "docker-compose.yml: postgres"; note if those tests are skipped/mocked

Non-obvious guardrails (beyond the schema):

- Use the highest patch for `python_version_tag` within the provided cap (major.minor).
- `test_worksubdir` is relative (e.g., ".", "backend"); choose the smallest subdir that contains and runs the unit tests.
- Prefer requirements files in `pip_deps`; ensure referenced files exist. Add direct packages only if necessary.
- Keep `project_apt_packages` minimal and justified by Python deps (e.g., psycopg2 -> libpq-dev; lxml -> libxml2-dev libxslt1-dev).
- `test_cmd` is argv only (no shell operators); editable install happens at runtime before `test_cmd` is executed, not during image build.
