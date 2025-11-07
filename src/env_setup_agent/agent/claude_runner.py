"""Claude agent runner with iteration support."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable, Awaitable

from ..core.models import Decision, DockerVars, generate_dummy_decision
from ..core.enums import Status
from ..core import schema as schema_mod

from ..utils.logging import get_logger
logger = get_logger()

# Utilities

def first_json_object(s: str) -> Dict[str, Any]:
    """
    Extract the first valid JSON object from a string.

    Args:
        s: String potentially containing JSON

    Returns:
        Parsed JSON object

    Raises:
        ValueError: If no valid JSON found
    """
    start = s.find("{")
    if start == -1:
        raise ValueError("no json")
    for end in range(len(s), start, -1):
        try:
            return json.loads(s[start:end])
        except json.JSONDecodeError:
            continue
    raise ValueError("no valid json")


def map_decision(obj: Dict[str, Any]) -> Decision:
    """
    Map JSON object to Decision dataclass.

    Args:
        obj: JSON object from agent

    Returns:
        Decision instance
    """
    err = schema_mod.validate_or_error(obj)
    if err:
        return Decision(Status.REFUSE, f"invalid output: {err}", None, {})

    status = Status(obj["status"])
    variables = None

    if status is Status.PROCEED:
        v = obj["variables"]
        variables = DockerVars(
            python_version_tag=v["python_version_tag"],
            test_worksubdir=v["test_worksubdir"],
            project_apt_packages=v.get("project_apt_packages", []),
            env_vars=v.get("env_vars", {}),
            pip_deps=v.get("pip_deps", []),
            install_editable=bool(v.get("install_editable", False)),
            pip_loc_e_dep=v.get("pip_loc_e_dep"),
            test_cmd=v.get("test_cmd", ["python", "-m", "pytest"])
        )

    return Decision(status, obj.get("reason"), variables, obj.get("evidence", {}))


# Prompt assembly


def assemble_initial_user(repo_task: str, policy: str, contract_json: str) -> str:
    """
    Assemble initial user prompt.

    Args:
        repo_task: Task description
        policy: Policy text
        contract_json: JSON schema contract

    Returns:
        Complete user prompt
    """
    return "\n\n".join([
        repo_task,
        "POLICY",
        policy,
        "CONTRACT",
        f"```json\n{contract_json}\n```",
        "Return only the JSON."
    ])


def assemble_iteration_user(prev_vars: DockerVars, build_tail: str, run_tail: str) -> str:
    """
    Assemble iteration prompt with logs.

    Args:
        prev_vars: Previous variables
        build_tail: Build log tail
        run_tail: Run log tail

    Returns:
        Iteration prompt
    """
    prev_json = json.dumps(asdict(prev_vars), indent=2)
    return f"""PREVIOUS VARIABLES
```json
{prev_json}
```

UPDATE (build/run logs, tails)

=== BUILD LOG ===
{build_tail}

=== RUN LOG ===
{run_tail}

Return ONLY the revised JSON per the same contract. If policy is violated, set status="refuse" with reason & evidence.
"""


# Agent class

class ClaudeRepoAgent:
    """
    Agent for scanning repositories and generating Docker variables.

    Uses Claude Agent SDK with read-only tools.
    """

    def __init__(self, repo_path: Path, model: Optional[str] = None):
        """
        Initialize agent.

        Args:
            repo_path: Path to repository
            model: Optional model name override
        """
        self.repo_path = Path(repo_path).resolve()
        self.model = model

    async def _ask(self, client: Any, user_text: str) -> Decision:
        """
        Ask Claude and parse response.

        Args:
            client: Claude SDK client
            user_text: User prompt

        Returns:
            Decision from agent
        """
        logger.debug(f"_ask(client={client}, user_text={user_text})")
        logger.debug("")

        # Import here to avoid requiring SDK at module level
        try:
            from claude_agent_sdk import AssistantMessage, TextBlock, ToolUseBlock
        except ImportError:
            # Fallback for development/testing
            return Decision(Status.REFUSE, "Claude SDK not available", None, {})

        await client.query(user_text)
        chunks: List[str] = []

        async for msg in client.receive_response():
            logger.debug(f"Claude response: ")
            if isinstance(msg, AssistantMessage):
                for blk in msg.content:
                    if isinstance(blk, TextBlock):
                        chunks.append(blk.text)
                        logger.debug(blk.text)
                    elif isinstance(blk, ToolUseBlock):
                        logger.debug(f"Tool call: {blk.name}({blk.input})")
            else:
                logger.debug(f"{msg}")

        try:
            raw = first_json_object("".join(chunks))
        except Exception as e:
            return Decision(Status.REFUSE, f"invalid output: {e}", None, {})

        return map_decision(raw)

    async def run(
        self,
        repo_name: str,
        commit_sha: str,
        py_cap_minor: Tuple[int, int],
        build_and_test_cb: Callable[[DockerVars], Awaitable[Tuple[bool, str, str, str]]],
        system_txt: str,
        task_tpl: str,
        policy_txt: str,
        contract_json: str,
        max_rounds: int = 3,
    ) -> Decision:
        """
        Run agent with iteration.

        Args:
            repo_name: Repository name
            commit_sha: Commit SHA
            py_cap_minor: Python version cap (major, minor)
            build_and_test_cb: Async callback (DockerVars) -> (ok, build_tail, run_tail, classification)
            max_rounds: Maximum iteration rounds
            task_tpl: Task template string
            policy_txt: Policy text
            contract_json: Contract JSON schema

        Returns:
            Final Decision
        """
        logger.debug(f"run(repo_name={repo_name}, commit_sha={commit_sha}, py_cap_minor={py_cap_minor}, max_rounds={max_rounds})")

        # Import here to avoid requiring SDK at module level
        try:
            from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
        except ImportError:
            return Decision(Status.REFUSE, "Claude SDK not available", None, {})

        logger.debug("")

        # Format initial prompt
        repo_task = task_tpl.format(
            repo_name=repo_name,
            commit_sha=commit_sha,
            python_cap_minor=py_cap_minor
        )
        user0 = assemble_initial_user(repo_task, policy_txt, contract_json)

        # Configure client
        options = ClaudeAgentOptions(
            # TODO: Use the provided system.md instead
            system_prompt=system_txt,
            allowed_tools=["Glob", "Grep", "Read"],
            permission_mode="plan",
            cwd=str(self.repo_path),
            model=self.model
        )

        async with ClaudeSDKClient(options=options) as client:
            decision = await self._ask(client, user0)
            # decision = generate_dummy_decision()

            if decision.status is Status.REFUSE:
                return decision

            rounds = 1
            while rounds <= max_rounds:
                assert decision.variables

                ok, build_tail, run_tail, classification = await build_and_test_cb(decision.variables)

                if ok or classification == "pytest_failed":
                    return decision

                user_iter = assemble_iteration_user(
                    decision.variables,
                    build_tail[-32000:],
                    run_tail[-32000:]
                )
                decision = await self._ask(client, user_iter)
                # decision = generate_dummy_decision()

                if decision.status is Status.REFUSE:
                    return decision

                rounds += 1

            return Decision(
                Status.REFUSE,
                f"max rounds {max_rounds} reached",
                None,
                {"loop": ["max_rounds_exhausted"]}
            )
