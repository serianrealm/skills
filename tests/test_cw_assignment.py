from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("cw_assignment", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_create_assignment_writes_required_contract(tmp_path: Path) -> None:
    module = load_module(Path("composer/bin/assignment.py"))

    assignment = tmp_path / ".agents" / "tasks" / "architecture" / "ASSIGNMENT.md"
    module.create_assignment(
        output_path=assignment,
        feature="checkout",
        task_slug="architecture",
        worker_type="architecturer",
        branch="architecture/checkout",
        worktree="/tmp/checkout-architecture",
        command="Design the API and tests.",
        objective="Add checkout support.",
        guidelines="Use TDD and keep public APIs narrow.",
        context="src/ contains the app code.",
        acceptance="Tests cover success and invalid input.",
        validation="pytest tests/checkout -q",
        forbidden="Do not implement business logic.",
        handoff="Summarize tests and interface changes.",
    )

    body = assignment.read_text(encoding="utf-8")
    for heading in module.REQUIRED_HEADINGS:
        assert f"## {heading}" in body
    assert "Feature: checkout" in body
    assert "Worker Type: architecturer" in body
    assert "Branch: architecture/checkout" in body
    assert "Attempt: 1" in body
    assert "Design the API and tests." in body


def test_append_revision_updates_current_command_and_log(tmp_path: Path) -> None:
    module = load_module(Path("composer/bin/assignment.py"))
    assignment = tmp_path / "ASSIGNMENT.md"
    module.create_assignment(
        output_path=assignment,
        feature="checkout",
        task_slug="develop",
        worker_type="developer",
        branch="develop/checkout",
        worktree="/tmp/checkout-develop",
        command="Implement the interface.",
        objective="Add checkout support.",
        guidelines="Follow existing style.",
        context="Read src/checkout.py.",
        acceptance="Composer will run tests.",
        validation="python -m compileall src",
        forbidden="Do not access tests.",
        handoff="Include changed files.",
    )

    module.append_revision(
        assignment_path=assignment,
        command="Fix the missing validation branch.",
        notes="Composer review found invalid coupons are accepted.",
    )

    body = assignment.read_text(encoding="utf-8")
    assert "Attempt: 2" in body
    assert "Fix the missing validation branch." in body
    assert "Composer review found invalid coupons are accepted." in body
    assert "### Attempt 1" in body
    assert "### Attempt 2" in body


def test_validate_assignment_rejects_missing_required_heading(tmp_path: Path) -> None:
    module = load_module(Path("composer/bin/assignment.py"))
    assignment = tmp_path / "ASSIGNMENT.md"
    assignment.write_text("# Broken\n\n## Task Identity\nOnly one heading.\n", encoding="utf-8")

    errors = module.validate_assignment(assignment)

    assert "missing heading: Current Command" in errors


def test_cli_create_writes_assignment(tmp_path: Path) -> None:
    assignment = tmp_path / "ASSIGNMENT.md"

    subprocess.run(
        [
            "python3",
            "composer/bin/assignment.py",
            "create",
            "--output-path",
            str(assignment),
            "--feature",
            "checkout",
            "--task-slug",
            "develop",
            "--worker-type",
            "developer",
            "--branch",
            "develop/checkout",
            "--worktree",
            "/tmp/checkout-develop",
            "--command",
            "Implement the interface.",
            "--objective",
            "Add checkout support.",
            "--guidelines",
            "Follow the interface.",
            "--context",
            "Use src/checkout.py.",
            "--acceptance",
            "Composer will verify behavior.",
            "--validation",
            "python -m compileall src",
            "--forbidden",
            "Do not access tests.",
            "--handoff",
            "Write HANDOFF.md.",
        ],
        check=True,
    )

    assert "Feature: checkout" in assignment.read_text(encoding="utf-8")
