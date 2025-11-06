POLICY

- Proceed only if tests can run with: Python interpreter, Python deps, system libs, and direct pytest.
- Refuse if: no tests; or external long-running services are required unless tests self-spawn/manage them.
- You should install directly in the docker's env, instead of in a virtial env running in docker.
- No services started in Dockerfile.
- Base: python:X.Y-slim with X.Y <= the detected upper bound.
- If external services are detected (docker-compose, GitHub Actions services, etc.) but tests use mocking or self-contained test fixtures, you may proceed.
- If tests require actual running databases, message queues, or other services that are NOT mocked, you must refuse.
- If a test is skipped, ignore it and don't refuse because of its content. However, if all tests are skipped, refuse to generate.
