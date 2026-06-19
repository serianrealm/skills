#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, NamedTuple


WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
PATH_TOOLS = WRITE_TOOLS | {"Read", "Grep", "Glob"}
WORKER_ROLES = {"architecturer", "developer"}
ALL_ROLES = WORKER_ROLES | {"composer"}
TEST_COMMAND_RE = re.compile(
    r"\b(pytest|tox|nox|jest|vitest|mocha|ava|tap|go\s+test|cargo\s+test|npm\s+test|pnpm\s+test|yarn\s+test)\b"
)


class Decision(NamedTuple):
    allowed: bool
    message: str = ""


def evaluate_event(event: dict[str, Any]) -> Decision:
    cwd = Path(str(event.get("cwd") or os.getcwd())).resolve()
    role = _agent_role(event, cwd)
    if role not in ALL_ROLES:
        return Decision(True)

    hook_event = str(event.get("hook_event_name") or "")
    if hook_event == "Stop" and role in WORKER_ROLES:
        return _evaluate_worker_stop(event, cwd)

    tool_name = str(event.get("tool_name") or "")
    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}

    if role == "composer":
        composer_decision = _evaluate_composer(tool_name, tool_input, cwd)
        if not composer_decision.allowed:
            return composer_decision

    if role in WORKER_ROLES:
        assignment_decision = _prevent_worker_assignment_write(tool_name, tool_input, cwd)
        if not assignment_decision.allowed:
            return assignment_decision

    if role == "developer":
        return _evaluate_developer(tool_name, tool_input, cwd)

    return Decision(True)


def _evaluate_composer(tool_name: str, tool_input: dict[str, Any], cwd: Path) -> Decision:
    if tool_name in WRITE_TOOLS:
        for raw_path in _paths_from_tool_input(tool_input):
            rel = _relative_path(raw_path, cwd)
            if rel is None or not _is_under_allowed_composer_root(rel):
                return Decision(False, "composer may only write docs/**, .agents/**, and CHANGELOG.md")

    if tool_name == "Bash":
        command = str(tool_input.get("command") or "")
        if _looks_like_composer_code_write(command):
            return Decision(False, "composer may not mutate project code through Bash")

    return Decision(True)


def _evaluate_developer(tool_name: str, tool_input: dict[str, Any], cwd: Path) -> Decision:
    if tool_name in PATH_TOOLS:
        for raw_path in _paths_from_tool_input(tool_input):
            if _is_test_path(raw_path, cwd):
                return Decision(False, "developer may not access tests")

    if tool_name == "Bash":
        command = str(tool_input.get("command") or "")
        if TEST_COMMAND_RE.search(command):
            return Decision(False, "developer may not run test commands")
        if _command_mentions_tests(command):
            return Decision(False, "developer may not access tests")

    return Decision(True)


def _prevent_worker_assignment_write(
    tool_name: str,
    tool_input: dict[str, Any],
    cwd: Path,
) -> Decision:
    if tool_name not in WRITE_TOOLS:
        return Decision(True)
    for raw_path in _paths_from_tool_input(tool_input):
        rel = _relative_path(raw_path, cwd)
        if rel is not None and str(rel).endswith(".agents/tasks/ASSIGNMENT.md"):
            return Decision(False, "workers may not modify ASSIGNMENT.md")
        if rel is not None and rel.name == "ASSIGNMENT.md" and ".agents" in rel.parts:
            return Decision(False, "workers may not modify ASSIGNMENT.md")
    return Decision(True)


def _evaluate_worker_stop(event: dict[str, Any], cwd: Path) -> Decision:
    task_slug = str(event.get("task_slug") or os.environ.get("CW_TASK_SLUG") or "").strip()
    if not task_slug:
        marker = cwd / ".agents" / "current-task"
        if marker.is_file():
            task_slug = marker.read_text(encoding="utf-8").strip()
    if not task_slug:
        return Decision(False, "worker stop blocked: missing task slug")

    handoff = cwd / ".agents" / "tasks" / task_slug / "HANDOFF.md"
    if not handoff.is_file():
        return Decision(False, f"worker stop blocked: missing .agents/tasks/{task_slug}/HANDOFF.md")
    return Decision(True)


def _agent_role(event: dict[str, Any], cwd: Path) -> str:
    candidates = [
        event.get("agent_name"),
        event.get("agent"),
        event.get("subagent_name"),
        os.environ.get("CW_AGENT_ROLE"),
    ]
    metadata = event.get("metadata")
    if isinstance(metadata, dict):
        candidates.extend([metadata.get("agent_name"), metadata.get("agent")])
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip().lower() in ALL_ROLES:
            return candidate.strip().lower()
    marker = cwd / ".agents" / "current-role"
    if marker.is_file():
        marker_value = marker.read_text(encoding="utf-8").strip().lower()
        if marker_value in ALL_ROLES:
            return marker_value
    return ""


def _paths_from_tool_input(tool_input: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("file_path", "path", "notebook_path", "pattern"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        for edit in edits:
            if isinstance(edit, dict):
                value = edit.get("file_path") or edit.get("path")
                if isinstance(value, str) and value.strip():
                    values.append(value.strip())
    return values


def _relative_path(raw_path: str, cwd: Path) -> Path | None:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = cwd / candidate
    try:
        return candidate.resolve(strict=False).relative_to(cwd)
    except ValueError:
        return None


def _is_under_allowed_composer_root(rel: Path) -> bool:
    return rel.parts[:1] in {("docs",), (".agents",)} or rel == Path("CHANGELOG.md")


def _is_test_path(raw_path: str, cwd: Path) -> bool:
    rel = _relative_path(raw_path, cwd)
    text = raw_path.replace("\\", "/")
    parts = set(text.split("/"))
    if rel is not None:
        text = str(rel).replace("\\", "/")
        parts = set(rel.parts)
    return (
        "tests" in parts
        or "__tests__" in parts
        or ".test." in text
        or ".spec." in text
        or text.endswith("_test.py")
    )


def _command_mentions_tests(command: str) -> bool:
    normalized = command.replace("\\", "/")
    return bool(re.search(r"(^|[\s./])(__tests__|tests)(/|\s|$)", normalized)) or bool(
        re.search(r"\.(test|spec)\.", normalized)
    )


def _looks_like_composer_code_write(command: str) -> bool:
    if not re.search(r"\b(touch|mkdir|rm|mv|cp|tee|sed|perl|python|python3|node)\b", command):
        return False
    return bool(re.search(r"(^|[\s'\"./])(src|tests|lib|app)(/|\s|$)", command))


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(json.dumps({"decision": "block", "reason": f"invalid hook JSON: {exc}"}))
        raise SystemExit(2)
    decision = evaluate_event(event)
    if decision.allowed:
        print(json.dumps({"decision": "approve"}))
        return
    print(json.dumps({"decision": "block", "reason": decision.message}))
    raise SystemExit(2)


if __name__ == "__main__":
    main()
