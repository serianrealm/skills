#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

from analyzer_common import (
    LANGUAGE_BY_SUFFIX,
    emit_json,
    env_names_from_ast,
    iter_repo_files,
    load_pyproject,
    read_text,
    relpath,
    repo_root,
    repository_snapshot,
    run_git,
)


def collect_repository_facts(repo: Path) -> dict[str, Any]:
    repo = repo_root(repo)
    files = iter_repo_files(repo)
    pyproject = load_pyproject(repo)

    languages = sorted(
        {
            LANGUAGE_BY_SUFFIX[path.suffix]
            for path in files
            if path.suffix in LANGUAGE_BY_SUFFIX
        }
    )
    package_managers = []
    for marker in ["pyproject.toml", "poetry.lock", "requirements.txt", "package.json", "pnpm-lock.yaml", "yarn.lock", "Cargo.toml", "go.mod"]:
        if (repo / marker).is_file():
            package_managers.append(marker)

    build_commands: list[str] = []
    test_commands: list[str] = []
    lint_commands: list[str] = []
    typecheck_commands: list[str] = []

    if (repo / "pyproject.toml").is_file():
        build_commands.append("python -m build")
        if (repo / "tests").is_dir() or "tool" in pyproject and "pytest" in pyproject.get("tool", {}):
            test_commands.append("pytest")
        if "ruff" in pyproject.get("tool", {}):
            lint_commands.append("ruff check .")
        if "mypy" in pyproject.get("tool", {}):
            typecheck_commands.append("mypy .")

    package_json = repo / "package.json"
    if package_json.is_file():
        try:
            scripts = json.loads(package_json.read_text(encoding="utf-8")).get("scripts", {})
        except json.JSONDecodeError:
            scripts = {}
        for name, command in scripts.items():
            if "build" in name:
                build_commands.append(f"npm run {name}")
            if "test" in name:
                test_commands.append(f"npm run {name}")
            if "lint" in name:
                lint_commands.append(f"npm run {name}")
            if "type" in name:
                typecheck_commands.append(f"npm run {name}")

    entry_points: list[dict[str, str]] = []
    scripts = pyproject.get("project", {}).get("scripts", {})
    for name, target in sorted(scripts.items()):
        entry_points.append({"kind": "python_script", "name": name, "target": target})

    config_files = [
        relpath(repo, path)
        for path in files
        if path.name
        in {
            "pyproject.toml",
            "package.json",
            "tsconfig.json",
            "ruff.toml",
            ".ruff.toml",
            "mypy.ini",
            "pytest.ini",
            "Dockerfile",
            "docker-compose.yml",
            ".mcp.json",
            "CLAUDE.md",
            "AGENTS.md",
        }
        or path.parent.name in {".github", ".claude", ".agents", ".codex", ".devcontainer"}
    ]

    env_names: set[str] = set()
    for path in files:
        if path.suffix != ".py":
            continue
        try:
            tree = ast.parse(read_text(path))
        except SyntaxError:
            continue
        for name, _line in env_names_from_ast(tree):
            env_names.add(name)

    test_dirs = [relpath(repo, path) for path in repo.iterdir() if path.is_dir() and path.name in {"tests", "test"}]
    test_naming = ["test_*.py", "*_test.py"] if "Python" in languages else []

    facts = {
        "repository_snapshot": repository_snapshot(repo),
        "repository_facts": {
            "languages": languages,
            "package_managers": package_managers,
            "build_commands": build_commands,
            "test_commands": test_commands,
            "lint_commands": lint_commands,
            "typecheck_commands": typecheck_commands,
            "entry_points": entry_points,
            "config_files": sorted(config_files),
            "environment_variables": sorted(env_names),
            "git_worktrees": run_git(repo, ["worktree", "list", "--porcelain"]).splitlines(),
            "git_branches": run_git(repo, ["branch", "--format", "%(refname:short)"]).splitlines(),
            "ci_configuration": [relpath(repo, path) for path in files if ".github/workflows" in relpath(repo, path)],
            "runtime_entry_points": entry_points,
            "test_directories": test_dirs,
            "test_naming_conventions": test_naming,
        },
        "evidence": {
            "claims": [
                {
                    "text": "Repository facts were collected through local filesystem, Git, and manifest inspection.",
                    "type": "static_fact",
                    "confidence": "high",
                    "evidence": ["git:rev-parse", "filesystem:manifest-scan"],
                }
            ],
            "low_confidence_items": [],
        },
    }
    return facts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect deterministic repository facts.")
    parser.add_argument("--repo", default=".", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    emit_json(collect_repository_facts(args.repo))


if __name__ == "__main__":
    main()
