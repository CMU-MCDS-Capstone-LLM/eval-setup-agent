#!/usr/bin/env bash
set -euo pipefail

# Build the Docker image
export DOCKER_BUILDKIT=1
docker build -f /home/eiger/CMU/2025_Spring/11634_Capstone/playground/eval_env_setup/demo/new-example/envs/backup_alice-biometrics_petisco__9abf7b1f6ef8c55bdddcb9a5c2eff513f6a93130/Dockerfile -t envsetup/alice-biometrics_petisco__9abf7b1f6ef8c55bdddcb9a5c2eff513f6a93130:tests /home/eiger/CMU/2025_Spring/11634_Capstone/playground/eval_env_setup/demo/new-example/repos/alice-biometrics_petisco__9abf7b1f6ef8c55bdddcb9a5c2eff513f6a93130
