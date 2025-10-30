# syntax=docker/dockerfile:1.7
{# REQUIRED (no defaults):
   python_version_tag          # e.g. "3.12-slim"
   app_dir                     # e.g. "/app"
   app_user                    # e.g. "appuser"
   copy_src_path               # e.g. "."
   test_workdir                # where pytest runs (often same as app_dir)
   project_apt_packages        # list[str], can be empty but must be defined
   env_vars                    # dict[str,str], required project/runtime env vars
   pip_deps                    # ordered list[str] of pip install args (e.g. "-r requirements.txt", "--no-deps pkg==1.2.3")
#}

ARG PYTHON_VERSION={{ python_version_tag }}
FROM python:${PYTHON_VERSION}

# Base ENV (overridable at runtime)
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8
{%- for k, v in env_vars.items() %}
ENV {{ k }}={{ v }}
{%- endfor %}

# APT layer 1: stable toolchain
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      pkg-config \
      git \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# APT layer 2: project-specific native deps
RUN apt-get update && apt-get install -y --no-install-recommends \
{%- for p in project_apt_packages %}
      {{ p }} \
{%- endfor %}
    && rm -rf /var/lib/apt/lists/*

WORKDIR {{ app_dir }}
COPY {{ copy_src_path }} {{ app_dir }}/

# Pip (Python 3) — install as root, then drop privileges
RUN python -m pip install --upgrade pip
{%- for step in pip_deps %}
RUN set -eux; echo "+ pip install {{ step }}"; pip install {{ step }};
{%- endfor %}

# Create non-root user and switch
ARG APP_USER={{ app_user }}
RUN useradd -m ${APP_USER} && chown -R ${APP_USER}:${APP_USER} {{ app_dir }}
USER ${APP_USER}

# Run tests
WORKDIR {{ test_workdir }}
CMD ["python","-m","pytest"]
