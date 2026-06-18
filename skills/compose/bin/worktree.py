#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


SLUG_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def validate_slug(value: str) -> list[str]:
    errors: list[str] = []
    if not value:
        errors.append("slug must not be empty")
    if ".." in value:
        errors.append("slug must not contain '..'")
    if value.startswith(("-", ".", "/")) or value.endswith(("/", ".")):
        errors.append("slug must not start with '-', '.', '/' or end with '/' or '.'")
    if "/" in value:
        errors.append("slug must not contain '/'")
    if SLUG_RE.fullmatch(value) is None:
        errors.append("slug must use letters, digits, '.', '_' or '-'")
    return errors


def worker_branch(task_slug: str, feature: str) -> str:
    task_errors = validate_slug(task_slug)
    feature_errors = validate_slug(feature)
    if task_errors or feature_errors:
        raise ValueError("; ".join(task_errors + feature_errors))
    return f"{task_slug}/{feature}"


def create_feature_branch(feature: str, base: str = "main") -> None:
    errors = validate_slug(feature)
    if errors:
        raise ValueError("; ".join(errors))
    subprocess.run(["git", "show-ref", "--verify", f"refs/heads/{feature}"], check=False)
    result = subprocess.run(
        ["git", "rev-parse", "--verify", feature],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode == 0:
        return
    subprocess.run(["git", "branch", feature, base], check=True)


def create_worker_worktree(task_slug: str, feature: str, worktree_path: Path) -> str:
    branch = worker_branch(task_slug, feature)
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "worktree", "add", "-b", branch, str(worktree_path), feature], check=True)
    return branch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Composer git branches and worktrees.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    feature = subcommands.add_parser("feature-branch")
    feature.add_argument("feature")
    feature.add_argument("--base", default="main")
    worker = subcommands.add_parser("worker-worktree")
    worker.add_argument("task_slug")
    worker.add_argument("feature")
    worker.add_argument("worktree_path", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "feature-branch":
        create_feature_branch(args.feature, args.base)
        return
    branch = create_worker_worktree(args.task_slug, args.feature, args.worktree_path)
    print(branch)


if __name__ == "__main__":
    main()
