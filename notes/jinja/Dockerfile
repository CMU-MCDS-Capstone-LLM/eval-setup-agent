# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.11.13-slim
FROM python:${PYTHON_VERSION}

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8
ENV aaa="111"
ENV bbb="bbb-222"
ENV ccc="[1, 2, 3]"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      build-essential pkg-config git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      astgrep \
      tree \
      ripgrep \
    && rm -rf /var/lib/apt/lists/*

ARG APP_USER=appuser
RUN useradd -m ${APP_USER} && mkdir -p /workspace && chown -R ${APP_USER}:${APP_USER} /workspace
USER ${APP_USER}
ENV XDG_CACHE_HOME=/home/${APP_USER}/.cache

# Enforece installation of pytest, pytest-cov, coverage, so that testing agent can obtain coverage report of pytest
RUN --mount=type=cache,target=/home/${APP_USER}/.cache/pip
    bash -lc 'set -euo pipefail; \
      python -m pip install --upgrade pip; \
      echo "+ pip install pytest pytest-cov coverage"; \
      pip install pytest pytest-cov coverage; \
      true'

RUN --mount=type=cache,target=/home/${APP_USER}/.cache/pip \
    --mount=type=bind,source=repos/<myrepo>,target=/workspace,rw \
    bash -lc 'set -euo pipefail; \
      cd "/workspace"; \
      echo "+ pip install numpy"; \
      pip install numpy; \
      echo "+ pip install pandas"; \
      pip install pandas; \
      echo "+ pip install mypackage==3.1.10"; \
      pip install mypackage==3.1.10; \
      echo "+ pip install -e ."; \
      pip install -e .; \
      true'

WORKDIR /workspace

CMD ["python", "-m", "pytest"]