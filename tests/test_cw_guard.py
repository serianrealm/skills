from __future__ import annotations

import importlib.util
from pathlib import Path


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("cw_guard", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def base_event(tmp_path: Path, agent: str, tool_name: str, tool_input: dict) -> dict:
    return {
        "cwd": str(tmp_path),
        "hook_event_name": "PreToolUse",
        "agent_name": agent,
        "tool_name": tool_name,
        "tool_input": tool_input,
    }


def test_composer_may_write_docs_and_agents_only(tmp_path: Path) -> None:
    module = load_module(Path("plugins/composer/bin/guard.py"))

    allowed = module.evaluate_event(
        base_event(tmp_path, "composer", "Write", {"file_path": str(tmp_path / "docs/spec.md")})
    )
    changelog_allowed = module.evaluate_event(
        base_event(tmp_path, "composer", "Write", {"file_path": str(tmp_path / "CHANGELOG.md")})
    )
    blocked = module.evaluate_event(
        base_event(tmp_path, "composer", "Edit", {"file_path": str(tmp_path / "src/app.py")})
    )

    assert allowed.allowed is True
    assert changelog_allowed.allowed is True
    assert blocked.allowed is False
    assert "composer may only write docs/**, .agents/**, and CHANGELOG.md" in blocked.message


def test_developer_cannot_access_tests_or_run_tests(tmp_path: Path) -> None:
    module = load_module(Path("plugins/composer/bin/guard.py"))

    read_tests = module.evaluate_event(
        base_event(tmp_path, "developer", "Read", {"file_path": str(tmp_path / "tests/test_app.py")})
    )
    run_tests = module.evaluate_event(
        base_event(tmp_path, "developer", "Bash", {"command": "pytest tests -q"})
    )

    assert read_tests.allowed is False
    assert "developer may not access tests" in read_tests.message
    assert run_tests.allowed is False
    assert "developer may not run test commands" in run_tests.message


def test_worker_cannot_modify_assignment(tmp_path: Path) -> None:
    module = load_module(Path("plugins/composer/bin/guard.py"))

    blocked = module.evaluate_event(
        base_event(
            tmp_path,
            "architecturer",
            "Edit",
            {"file_path": str(tmp_path / ".agents/tasks/architecture/ASSIGNMENT.md")},
        )
    )

    assert blocked.allowed is False
    assert "workers may not modify ASSIGNMENT.md" in blocked.message


def test_worker_stop_requires_handoff(tmp_path: Path) -> None:
    module = load_module(Path("plugins/composer/bin/guard.py"))
    event = {
        "cwd": str(tmp_path),
        "hook_event_name": "Stop",
        "agent_name": "developer",
        "task_slug": "develop",
    }

    blocked = module.evaluate_event(event)
    handoff = tmp_path / ".agents" / "tasks" / "develop" / "HANDOFF.md"
    handoff.parent.mkdir(parents=True)
    handoff.write_text("# Handoff\n", encoding="utf-8")
    allowed = module.evaluate_event(event)

    assert blocked.allowed is False
    assert "missing .agents/tasks/develop/HANDOFF.md" in blocked.message
    assert allowed.allowed is True
