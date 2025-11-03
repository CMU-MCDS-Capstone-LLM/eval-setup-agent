"""Repository detection utilities."""

from .tests_detector import find_tests
from .python_version import detect_python_version
from .dep_files import find_dependency_files
from .sys_pkgs import infer_system_packages
from .services import detect_service_indicators
from .facts import gather_facts

__all__ = [
    "find_tests",
    "detect_python_version",
    "find_dependency_files",
    "infer_system_packages",
    "detect_service_indicators",
    "gather_facts",
]
