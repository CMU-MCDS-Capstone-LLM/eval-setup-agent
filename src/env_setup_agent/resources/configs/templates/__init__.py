from pathlib import Path

DEFAULT_TEMPLATES_DIR = Path(__file__).resolve().parent


def get_default_dockerfile_tpl_path() -> Path:
    return DEFAULT_TEMPLATES_DIR / "dockerfile.template.j2"


def get_default_build_script_tpl_path() -> Path:
    return DEFAULT_TEMPLATES_DIR / "build.sh.template.j2"


def get_default_run_script_tpl_path() -> Path:
    return DEFAULT_TEMPLATES_DIR / "run.sh.template.j2"
