You are generating a **Dockerfile** for a single Python repository so that, **after build**, we can simply run tests by executing `python -m pytest` inside the container. Proceed **only** if tests can run with:

* Python interpreter (≤ the allowed version you infer),
* Python dependencies,
* system libraries (client libs, compilers, headers, etc.),
* and `pytest` executed directly.

**You must refuse** if:

* No unit tests exist in the repo.
* The tests require any **separate long-running service** to be started by the image/container (e.g., Postgres, MySQL, Redis, Kafka, Elasticsearch, MinIO, LocalStack, Selenium grid, etc.), **unless** the tests themselves start/stop a helper process via `subprocess.Popen` (or equivalent) as part of their own fixtures/workflow.
* The repo tooling (e.g., tox/Poetry) **requires** a virtual environment or orchestration you cannot replicate natively; you must not create or use a virtual environment inside the image.

You may assume the repository is already cloned at ``

## Repository context (inputs)

* Repo name: `milvus-io/bootcamp`
* Target commit sha: `a7f4c3f13e007116d88d9a2776f471a4e4f1fc81`
* Target commit timestamp (UTC): `2021-09-01T06:32:04Z`
* Repo is cloned locally at `examples/repos/milvus-io_bootcamp__a7f4c3f13e007116d88d9a2776f471a4e4f1fc81`
* Based on the repo commit timestamp, the **latest possible Python minor version** is `3.9`. Choose the **highest available patch** within the selected minor.
* Working directory during build/run is the repo root.

## What you MUST detect

1. **Test existence**

   * Confirm at least one of:
     * a `tests/` or `test/` directory containing `test_*.py` or `*_test.py`, or
     * a CI config that runs `pytest` on this repo with actual tests present.
   * If no tests are found, **refuse** with a clear explanation.

2. **Python version**

* **Read in this order (first conclusive hit wins):** `.python-version`; `pyproject.toml` (`project.requires-python` or `tool.poetry.dependencies.python`); `Pipfile` (`[requires].python_version`); `setup.cfg`/`setup.py` (`python_requires`); `tox.ini` (`basepython` for the matching env or `envlist` markers like `py311`); `poetry.lock` (if it records a Python constraint in metadata); `.tool-versions` (asdf); `runtime.txt`; **virtual-env metadata** such as `.venv/pyvenv.cfg` or `.tox/*/pyvenv.cfg` (use as lowest-priority hints); CI configs (GitHub Actions, CircleCI).
* Upper-bound the chosen version by `3.9` and pick the highest patch in that minor (e.g., base image `python:X.Y-slim`).

3. **Dependency manager & lockfiles**

   * Detect `pyproject.toml` (PEP 621/Poetry), `requirements*.txt`, `Pipfile`, `setup.cfg`, `setup.py`.
   * Ensure **test dependencies** are installed (e.g., `requirements-dev.txt`, extras like `.[test]`, or `[tool.poetry.group.dev]`).

4. **System packages**

   * Infer from deps: e.g., `build-essential`, `gcc`, `pkg-config`, `libssl-dev`, `libffi-dev`, `zlib1g-dev`, `libjpeg-dev`, `libxml2-dev`, `libxslt1-dev`, `libpq5` (client), `gfortran`, `libopenblas-dev`.
   * Install only what’s necessary for building/running **without starting external services**.

5. **Service requirements (refusal checks)**

   * **Refuse** if you detect the need for any external daemon **unless tests self-spawn it**:

     * Files like `docker-compose*.yml`, `.github/workflows/*` with `services:`, `.circleci/*`, `Makefile` targets that start DBs/brokers.
     * Environment variables that point to network services (`DATABASE_URL`, `REDIS_URL`, `ELASTICSEARCH_URL`, `KAFKA_BOOTSTRAP_SERVERS`, `S3_ENDPOINT_URL`, etc.) **and** no evidence tests mock or spawn the service themselves.
     * Testcontainers usage (requires external Docker daemon).
     * Docs/README that instruct “start X, then run tests”.
   * **Allowed**: tests that **programmatically** start a helper server/binary via `subprocess.Popen(...)` and wait for readiness on `127.0.0.1`. In such cases, ensure the **binary and libs** exist in the image; you do **not** start any daemons in the Dockerfile/entrypoint.

## What to do after successfully generating Dockerfile

If you managed to generate dockerfile, you should then build and run it, fix errors until the test runs successfully. Note that it's OK if some unit tests fail, but it shouldn't fail due to dependency error.

If you can't get it fixed the dependency-induced test error after 3 attempts, you should refuse and create a summary of failure reason.

Note that you should first **build** the dockerfile you generate, then **run the unit test by spinning up the container**. You should not directly run on the host system.

## Output format (write files to the exact paths provided)

1. **Decision file**

   * If you can generate a Dockerfile, and successfully build and run it: create an empty file at `examples/envs/milvus-io_bootcamp__a7f4c3f13e007116d88d9a2776f471a4e4f1fc81/_SUCCESS`.
   * If you must refuse: create an empty file at `examples/envs/milvus-io_bootcamp__a7f4c3f13e007116d88d9a2776f471a4e4f1fc81/_FAILURE`.

2. **Summary file**

   * Write a concise markdown summary to `examples/envs/milvus-io_bootcamp__a7f4c3f13e007116d88d9a2776f471a4e4f1fc81/summary.md` explaining your decision.

     * On success: list the detected constraints, chosen Python version, key system packages, and how you verified no external services are required.
     * On refusal: list the reason why the policy is violated. If due to files/lines/configs that imply external services, list at least one of them explicitly
3. **Dockerfile (only on success)**

   * Write a complete, ready-to-build `Dockerfile` to `examples/envs/milvus-io_bootcamp__a7f4c3f13e007116d88d9a2776f471a4e4f1fc81/Dockerfile`.
4. **Build & Run script (only on success)**

   * Write a small shell snippet to `examples/envs/milvus-io_bootcamp__a7f4c3f13e007116d88d9a2776f471a4e4f1fc81/run_instructions.sh` containing:

     * one `docker build`
     * one `docker run` that executes `python -m pytest` by default.

## Implementation rules for the Dockerfile

* Base: `python:X.Y-slim` (X.Y ≤ `3.9`).
* Set: `PIP_NO_CACHE_DIR=1`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`, `DEBIAN_FRONTEND=noninteractive`.
* Install only necessary **system packages**; clean apt lists.
* Create a **non-root** user and run as that user.
* **Strictly no virtual environment** inside the image. Install dependencies into the native interpreter. If the repo tooling demands a venv/tox-managed env you cannot replicate natively, **refuse**.
* **Do not** start or supervise services in the Dockerfile/entrypoint.
* Default command must be:

  ```
  CMD ["python", "-m", "pytest"]
  ```

## Note on Python 2

If the detected or inferred interpreter version belongs to **Python 2.x**, you must **not** use an official `python:2.x` image tag.
Those images are deprecated and rely on obsolete Debian repositories that no longer build reliably.

Instead, you must **build Python 2 from source** inside a modern base image (e.g. `debian:bullseye-slim` or `debian:bookworm-slim`) using the following pattern (we use python 2.7.18 as an example, you should adapt based on specific cases):

```dockerfile
# Example snippet for Python 2.x
FROM debian:bullseye-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential gcc make wget libssl-dev zlib1g-dev libffi-dev \
      libbz2-dev libreadline-dev libsqlite3-dev ca-certificates curl \
  && rm -rf /var/lib/apt/lists/*

# Build and install Python 2 from source
RUN set -eux; \
    PYVER=2.7.18; \
    wget -q https://www.python.org/ftp/python/${PYVER}/Python-${PYVER}.tgz; \
    tar -xf Python-${PYVER}.tgz; \
    cd Python-${PYVER}; \
    ./configure --prefix=/usr/local --enable-unicode=ucs4 --with-ensurepip=no; \
    make -j"$(nproc)"; \
    make install; \
    cd ..; rm -rf Python-${PYVER}*; \
    [ -e /usr/local/bin/python ] || ln -s /usr/local/bin/python2.7 /usr/local/bin/python
```

**Key rules:**

* Always build from source instead of `FROM python:2.x`.
* Pin the version explicitly (e.g., `2.7.18`).
* Prefer `python2.7` explicitly in all commands (`CMD ["python2.7", "-m", "pytest"]`).
* Install minimal build tools and clean them after installation to reduce image size.
* This method ensures Python 2 environments build reproducibly even after legacy repos are removed.

---

## EXAMPLE A — PROCEED (tests self-spawn a local helper)

> Note that the exact choice of dependencies (e.g. python version) in the examples are not relevant to our target repo.

**Context**

* `pyproject.toml` specifies `requires-python = ">=3.9,<3.12"`.
* Based on commit time, `max_python_ver` = 3.11 → choose latest 3.11 patch.
* `tests/conftest.py` starts a mock HTTP server via `subprocess.Popen([...])` and waits on `127.0.0.1`; no external endpoints present.
* `requirements-dev.txt` includes `pytest`, `requests`, `fakeredis`.

**Files to write**

* `envs/dummyauthor_dummyrepo__deadbeef/success`: create empty file.
* `envs/dummyauthor_dummyrepo__deadbeef/summary.md` (example content):

  ```markdown
  # Generation Summary — Success
  - Tests detected under `tests/` and runnable with `pytest`.
  - No external services required; helper server is self-spawned in tests.
  - Python bounds: `>=3.9,<3.12`, capped by `max_python_ver` → selected `3.11.latest`.
  - System packages: build-essential, libssl-dev, libffi-dev, zlib1g-dev, libxml2-dev, libxslt1-dev, libjpeg-turbo.
  - Policy satisfied: no venv, no container-managed services, default CMD runs `python -m pytest`.
  ```

* `envs/dummyauthor_dummyrepo__deadbeef/Dockerfile` (example content):

  ```dockerfile
  # syntax=docker/dockerfile:1.7
  ARG PYTHON_VERSION=3.11.9
  FROM python:${PYTHON_VERSION}-slim

  ENV DEBIAN_FRONTEND=noninteractive \
      PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

  RUN --mount=type=cache,target=/var/cache/apt \
      apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc pkg-config \
        libssl-dev libffi-dev zlib1g-dev \
        libxml2-dev libxslt1-dev \
        libjpeg62-turbo-dev \
        curl ca-certificates git \
      && rm -rf /var/lib/apt/lists/*

  RUN useradd -m appuser && mkdir -p /app && chown -R appuser:appuser /app
  WORKDIR /app
  USER appuser

  RUN python -m pip install --upgrade pip \
   && if [ -f requirements.txt ]; then pip install -r requirements.txt; fi \
   && if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi

  # Copy the full source last (from repos/<author>__<repo>)
  COPY --chown=appuser:appuser repos/dummyauthor_dummyrepo/ /app

  ENV PYTEST_ADDOPTS="-q"
  CMD ["python", "-m", "pytest"]
  ```

* `envs/dummyauthor_dummyrepo__deadbeef/run_instructions.sh` (example content):

  ```bash
  # Build (choose a patch <= max_python_ver)
  docker build -t dummyauthor_dummyrepo:tests -f <path to Dockerfile> .

  # Run tests (defaults to python -m pytest)
  docker run --rm dummyauthor_dummyrepo:tests
  ```

---

## EXAMPLE B — REFUSE (external service required)

**Context**

* `tests/integration/test_db.py` imports `psycopg2` and connects via `os.environ["DATABASE_URL"]`.

* `.github/workflows/ci.yml` declares:

  ```yaml
  services:
    postgres:
      image: postgres:15
  ```

* `docker-compose.yml` provisions `postgres`.

* No fixtures that self-spawn Postgres; no SQLite fallback.

**Files to write**

* `envs/dummyauthor_dummyrepo__deadbeef/failure`: create empty file.

* `envs/dummyauthor_dummyrepo__deadbeef/summary.md` (example content):

  ```markdown
  # Generation Summary — Refused
  **Reason**: The test suite requires a Postgres service at runtime, which violates the “no container-started services” policy.

  **Evidence**
  - `tests/integration/test_db.py` connects via `DATABASE_URL` (Postgres).
  - `.github/workflows/ci.yml` uses `services: postgres:15`.
  - `docker-compose.yml` defines a `postgres` service.
  **Resolution options**
  - Modify tests to self-spawn an ephemeral DB (not recommended for Postgres), or
  - Replace with pure mocks/in-process substitutes (e.g., SQLite), or
  - Relax the policy to allow supervised services in-container.
  ```

* Do **not** write `envs/dummyauthor_dummyrepo__deadbeef/Dockerfile` or `envs/dummyauthor_dummyrepo__deadbeef/run_instructions.sh`.

---

## Final reminders

* If **no unit tests** are present, refuse and document which checks failed (e.g., no `tests/` dir, no `test_*.py`, no CI invocation).
* It is acceptable if tests **use `subprocess.Popen` to start a helper** (e.g., a local HTTP stub or `redis-server`) and fully manage its lifecycle; ensure the necessary binaries/libs are installed, but **you do not start them** in the image.
* Never include credentials in the Dockerfile; allow runtime `docker run -e ...` overrides if needed.