"""Summary generation for environment setup results."""

from pathlib import Path
from .models import RepoSpec, Decision
from .enums import Status


def write_summary(env_dir: Path, spec: RepoSpec, decision: Decision) -> None:
    """
    Write a summary.md file for the generation result.

    Args:
        env_dir: Environment directory
        spec: Repository specification
        decision: Agent decision
    """
    p = env_dir / "summary.md"

    if decision.status is Status.PROCEED and decision.variables:
        v = decision.variables
        apt_list = ", ".join(v.project_apt_packages) if v.project_apt_packages else "(none)"
        pip_list = ", ".join(v.pip_deps) if v.pip_deps else "(none)"

        content = f"""# Generation Summary — Success

- Repo: {spec.repo_name} @ {spec.commit_sha}
- Python base: {v.python_version_tag}
- APT: {apt_list}
- Pip plan: {pip_list}
- Editable: {v.install_editable}
- Mount path: {v.mount_dir}
- Test workdir: {v.test_workdir}
"""
    else:
        evidence_lines = []
        for cat in decision.evidence:
            for e in decision.evidence[cat]:
                evidence_lines.append(f"- {e}")
        evidence_str = "\n".join(evidence_lines) if evidence_lines else "(none)"

        content = f"""# Generation Summary — Refused

Reason: {decision.reason or "(unspecified)"}

Evidence:
{evidence_str}
"""

    p.write_text(content)
