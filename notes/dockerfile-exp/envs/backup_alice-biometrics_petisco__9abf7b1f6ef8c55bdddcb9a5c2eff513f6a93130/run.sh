#!/usr/bin/env bash
set -euo pipefail

# # Run tests in container
# docker run --rm \
# 	-v "/home/eiger/CMU/2025_Spring/11634_Capstone/playground/eval_env_setup/demo/new-example/repos/alice-biometrics_petisco__9abf7b1f6ef8c55bdddcb9a5c2eff513f6a93130":"/workspace" \
# 	-w "/workspace" \
# 	envsetup/alice-biometrics_petisco__9abf7b1f6ef8c55bdddcb9a5c2eff513f6a93130:tests \
# 	bash -lc "pip install -e .[fixtures,rabbitmq,pymongo,elastic,sqlalchemy,fastapi,slack,redis,flask] && python -m pytest"

# Run tests in container
docker run -it --rm \
	-v "/home/eiger/CMU/2025_Spring/11634_Capstone/playground/eval_env_setup/demo/new-example/repos/alice-biometrics_petisco__9abf7b1f6ef8c55bdddcb9a5c2eff513f6a93130":"/workspace" \
	-w "/workspace" \
	envsetup/alice-biometrics_petisco__9abf7b1f6ef8c55bdddcb9a5c2eff513f6a93130:tests \
	bash
