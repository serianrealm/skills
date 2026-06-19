#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


REQUIRED_HEADINGS = [
    "Task Identity",
    "Current Command",
    "Objective Goal",
    "Implementation Guidelines",
    "Context Packet",
    "Acceptance Criteria",
    "Validation Commands",
    "Forbidden Actions",
    "Handoff Requirements",
    "Revision Log",
]


def create_assignment(
    *,
    output_path: Path,
    feature: str,
    task_slug: str,
    worker_type: str,
    branch: str,
    worktree: str,
    command: str,
    objective: str,
    guidelines: str,
    context: str,
    acceptance: str,
    validation: str,
    forbidden: str,
    handoff: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(
            [
                "# ASSIGNMENT",
                "",
                "## Task Identity",
                f"- Feature: {feature}",
                f"- Task Slug: {task_slug}",
                f"- Worker Type: {worker_type}",
                f"- Branch: {branch}",
                f"- Worktree: {worktree}",
                "",
                "## Current Command",
                "- Attempt: 1",
                "",
                command.strip(),
                "",
                "## Objective Goal",
                "",
                objective.strip(),
                "",
                "## Implementation Guidelines",
                "",
                guidelines.strip(),
                "",
                "## Context Packet",
                "",
                context.strip(),
                "",
                "## Acceptance Criteria",
                "",
                acceptance.strip(),
                "",
                "## Validation Commands",
                "",
                validation.strip(),
                "",
                "## Forbidden Actions",
                "",
                forbidden.strip(),
                "",
                "## Handoff Requirements",
                "",
                handoff.strip(),
                "",
                "## Revision Log",
                "",
                "### Attempt 1",
                "",
                command.strip(),
                "",
            ]
        ),
        encoding="utf-8",
    )


def append_revision(*, assignment_path: Path, command: str, notes: str) -> None:
    text = assignment_path.read_text(encoding="utf-8")
    errors = validate_assignment(assignment_path)
    if errors:
        raise ValueError("; ".join(errors))

    attempt = _next_attempt(text)
    updated_command = f"## Current Command\n- Attempt: {attempt}\n\n{command.strip()}\n\n"
    text = re.sub(
        r"## Current Command\n.*?(?=\n## Objective Goal\n)",
        updated_command,
        text,
        flags=re.DOTALL,
    )
    revision_entry = "\n".join(
        [
            f"### Attempt {attempt}",
            "",
            command.strip(),
            "",
            "Composer notes:",
            "",
            notes.strip(),
            "",
        ]
    )
    text = text.rstrip() + "\n\n" + revision_entry
    assignment_path.write_text(text, encoding="utf-8")


def validate_assignment(path: Path) -> list[str]:
    if not path.is_file():
        return [f"missing assignment file: {path}"]
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    for heading in REQUIRED_HEADINGS:
        if f"## {heading}" not in text:
            errors.append(f"missing heading: {heading}")
    return errors


def _next_attempt(text: str) -> int:
    attempts = [int(value) for value in re.findall(r"Attempt:\s*(\d+)", text)]
    return max(attempts, default=0) + 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage Composer ASSIGNMENT.md files.")
    subcommands = parser.add_subparsers(dest="command_name", required=True)

    create = subcommands.add_parser("create", help="Create a fresh ASSIGNMENT.md.")
    create.add_argument("--output-path", required=True, type=Path)
    create.add_argument("--feature", required=True)
    create.add_argument("--task-slug", required=True)
    create.add_argument(
        "--worker-type",
        required=True,
        choices=[
            "architecturer",
            "developer",
        ],
    )
    create.add_argument("--branch", required=True)
    create.add_argument("--worktree", required=True)
    create.add_argument("--command", required=True)
    create.add_argument("--objective", required=True)
    create.add_argument("--guidelines", required=True)
    create.add_argument("--context", required=True)
    create.add_argument("--acceptance", required=True)
    create.add_argument("--validation", required=True)
    create.add_argument("--forbidden", required=True)
    create.add_argument("--handoff", required=True)

    revise = subcommands.add_parser("revise", help="Append a composer revision.")
    revise.add_argument("--assignment-path", required=True, type=Path)
    revise.add_argument("--command", required=True)
    revise.add_argument("--notes", required=True)

    validate = subcommands.add_parser("validate", help="Validate an ASSIGNMENT.md.")
    validate.add_argument("assignment_path", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command_name == "create":
        values = vars(args).copy()
        values.pop("command_name")
        create_assignment(**values)
        return
    if args.command_name == "revise":
        append_revision(
            assignment_path=args.assignment_path,
            command=args.command,
            notes=args.notes,
        )
        return
    errors = validate_assignment(args.assignment_path)
    if errors:
        for error in errors:
            print(error)
        raise SystemExit(1)
    print(f"valid assignment: {args.assignment_path}")


if __name__ == "__main__":
    main()
