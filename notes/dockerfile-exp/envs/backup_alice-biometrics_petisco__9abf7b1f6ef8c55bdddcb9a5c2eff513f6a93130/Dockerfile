# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.9.19-slim
FROM python:${PYTHON_VERSION}

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

ENV PYTHONUNBUFFERED="1"
ENV SQL_SERVER="sqlite"
ENV SQL_DATABASE="petisco_test.db"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      build-essential pkg-config git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \      
    libssl-dev \      
    libffi-dev \      
    libyaml-dev \    
    && rm -rf /var/lib/apt/lists/*
ARG APP_USER=appuser
RUN useradd -m ${APP_USER} && mkdir -p /workspace && chown -R ${APP_USER}:${APP_USER} /workspace
USER ${APP_USER}
ENV XDG_CACHE_HOME=/home/${APP_USER}/.cache

# Separate step of upgrade pip for better caching
RUN --mount=type=cache,target=/home/${APP_USER}/.cache/pip \
    bash -lc 'set -euo pipefail; \
      python -m pip install --upgrade pip; \      
      true'

RUN --mount=type=cache,target=/home/${APP_USER}/.cache/pip \
    --mount=type=bind,source=.,target=/workspace,rw \
    bash -lc 'set -euo pipefail; \
      cd "/workspace"; \
      echo "+ pip install -r requirements/requirements.txt"; \
      pip install -r requirements/requirements.txt; \      
      echo "+ pip install -r requirements/dev.txt"; \
      pip install -r requirements/dev.txt; \      
      true'

# Only install pytest, pytest-cov, coverage if original repo doesn't have it
RUN --mount=type=cache,target=/home/${APP_USER}/.cache/pip \
    bash -lc 'set -euo pipefail; \
      echo "+ install pytest, pytest-cov, coverage only if not already installed"; \
      python -c "import pytest" || { echo "+ pip install pytest" && pip install pytest; }; \
      python -c "import pytest_cov" || { echo "+ pip install pytest-cov" && pip install pytest-cov; }; \
      python -c "import coverage" || { echo "+ pip install coverage" && pip install coverage; }; \
      true'


WORKDIR /workspace
CMD ["python", "-m", "pytest"]
