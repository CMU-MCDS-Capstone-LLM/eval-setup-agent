"""Classify test run outcomes."""


def classify_run_returncode(rc: int, log_tail: str) -> str:
    """
    Classify test run result based on return code and log content.

    Args:
        rc: Return code from docker run
        log_tail: Tail of the run log

    Returns:
        Classification string: "ok", "pytest_failed", "deps_error", or "build_failed"
    """
    if rc == 0:
        return "ok"

    # Check for dependency errors
    dependency_indicators = [
        "ModuleNotFoundError",
        "ImportError",
        "No matching distribution found",
        "ResolutionImpossible",
        "Could not find a version",
        "ERROR: Could not find",
    ]

    for indicator in dependency_indicators:
        if indicator in log_tail:
            return "deps_error"

    # Default to pytest failures
    return "pytest_failed"
