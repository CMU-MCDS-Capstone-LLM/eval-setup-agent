"""Core enumerations for env_setup_agent."""

from enum import Enum


class Status(str, Enum):
    """Status of the agent decision."""
    PROCEED = "proceed"
    REFUSE = "refuse"


class FailureReason(str, Enum):
    """Reasons for failure during environment setup."""
    NO_TESTS_FOUND = "no_tests_found"
    EXTERNAL_SERVICE_REQUIRED = "external_service_required"
    BUILD_FAILED = "build_failed"
    DEPENDENCY_INSTALL_FAILED = "dependency_install_failed"
    RUNTIME_DEPENDENCY_ERROR = "runtime_dependency_error"
    DOCKER_TIMEOUT = "docker_timeout"
    INVALID_AGENT_OUTPUT = "invalid_agent_output"
    POLICY_VIOLATION = "policy_violation"
    OTHER = "other"
