from __future__ import annotations

from pathlib import Path


WORKERS = {
    "architecturer",
    "developer",
}

REMOVED_WORKERS = {
    "researcher",
    "tester",
    "reviewer",
    "refactorer",
}


def test_worker_agent_files_exist() -> None:
    for worker in WORKERS:
        assert Path(f"composer/agents/{worker}.md").is_file()
    for worker in REMOVED_WORKERS:
        assert not Path(f"composer/agents/{worker}.md").exists()


def test_compose_skill_lists_expanded_worker_roster() -> None:
    body = Path("skills/compose/SKILL.md").read_text(encoding="utf-8")

    for worker in WORKERS:
        assert f"`{worker}`" in body
    for worker in REMOVED_WORKERS:
        assert f"`{worker}`" not in body
    assert "Launch only one worker class per batch" in body


def test_assignment_cli_accepts_all_worker_types() -> None:
    body = Path("composer/bin/assignment.py").read_text(encoding="utf-8")

    for worker in WORKERS:
        assert f'"{worker}"' in body
    for worker in REMOVED_WORKERS:
        assert f'"{worker}"' not in body


def test_guard_recognizes_all_worker_roles() -> None:
    body = Path("composer/bin/guard.py").read_text(encoding="utf-8")

    for worker in WORKERS:
        assert f'"{worker}"' in body
    for worker in REMOVED_WORKERS:
        assert f'"{worker}"' not in body


def test_compose_command_has_rich_initial_prompt() -> None:
    body = Path("composer/commands/compose.md").read_text(encoding="utf-8")

    assert "Initial composer prompt" in body
    assert "Worker roster" in body
    assert "Selection rules" in body
    assert "Final documentation loop" in body
