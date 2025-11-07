from pathlib import Path

DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parent

def get_default_contract_json_path() -> Path:
    return DEFAULT_PROMPTS_DIR / "contract.json"

def get_default_initial_tpl_path() -> Path:
    return DEFAULT_PROMPTS_DIR / "initial.md.j2"

def get_default_iterate_tpl_path() -> Path:
    return DEFAULT_PROMPTS_DIR / "iterate.md.j2"

def get_default_policy_prompt_path() -> Path:
    return DEFAULT_PROMPTS_DIR / "policy.md"

def get_default_repo_task_tpl_path() -> Path:
    return DEFAULT_PROMPTS_DIR / "repo_task.md.j2"

def get_default_system_prompt_path() -> Path:
    return DEFAULT_PROMPTS_DIR / "system.md"
