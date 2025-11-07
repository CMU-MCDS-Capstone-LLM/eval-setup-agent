#!/bin/bash

for file in $(
	find \
		"README.md" "pyproject.toml" \
		"demo/new-example/run_example.sh" \
		"demo/new-example/configs/" \
		"src/env_setup_agent" \
		-type f \
		-name "*.py" \
		-o -name "*.json" \
		-o -name "*.md" \
		-o -name "j2" \
		-o -name "*.toml" \
		-o -name "*.yaml" \
		-o -name "*.sh"
); do
	echo "###################"
	echo "$file"
	cat "$file"
	echo ""
done
