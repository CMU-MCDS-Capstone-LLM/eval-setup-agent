#!/usr/bin/env bash
#
# Example script to run env_setup_agent from YAML config
#

set -euo pipefail

CONFIG_PATH="/home/eiger/CMU/2025_Spring/11634_Capstone/playground/eval_env_setup/demo/example/configs/alice-biometrics_petisco__9abf7b1f6ef8c55bdddcb9a5c2eff513f6a93130/env-setup-agent-config.yaml"

# rm -rf "/home/eiger/CMU/2025_Spring/11634_Capstone/playground/eval_env_setup/demo/example/envs/alice-biometrics_petisco__9abf7b1f6ef8c55bdddcb9a5c2eff513f6a93130"
python -m "env_setup_agent.cli" "$CONFIG_PATH"
