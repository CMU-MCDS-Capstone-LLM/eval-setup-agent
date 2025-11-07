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
