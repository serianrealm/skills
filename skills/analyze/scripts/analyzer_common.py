from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GRAPH_VERSION = 1
SECRET_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "credentials",
    "credentials.json",
    "id_rsa",
    "id_ed25519",
}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
TEXT_SUFFIXES = {
    ".py",
    ".toml",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".ini",
    ".cfg",
    ".txt",
}
LANGUAGE_BY_SUFFIX = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".rb": "Ruby",
    ".php": "PHP",
    ".sh": "Shell",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def run_git(repo: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def repo_root(path: Path) -> Path:
    candidate = path.expanduser().resolve()
    root = run_git(candidate, ["rev-parse", "--show-toplevel"])
    if root:
        return Path(root).resolve()
    return candidate


def repository_snapshot(repo: Path) -> dict[str, Any]:
    status = run_git(repo, ["status", "--porcelain"])
    return {
        "repository_root": str(repo.resolve()),
        "branch": run_git(repo, ["branch", "--show-current"]) or "DETACHED_OR_UNKNOWN",
        "commit": run_git(repo, ["rev-parse", "HEAD"]) or "UNKNOWN",
        "dirty": bool(status),
        "generated_at": utc_now(),
    }


def is_secret_path(path: Path) -> bool:
    lowered = path.name.lower()
    return lowered in SECRET_FILE_NAMES or path.suffix.lower() in SECRET_SUFFIXES


def iter_repo_files(repo: Path) -> list[Path]:
    ignored_dirs = {
        ".git",
        ".analyzer",
        "__pycache__",
        ".pytest_cache",
        "node_modules",
        "dist",
        "build",
        ".venv",
        "venv",
    }
    files: list[Path] = []
    for path in repo.rglob("*"):
        rel_parts = path.relative_to(repo).parts
        if any(part in ignored_dirs for part in rel_parts):
            continue
        if path.is_file() and not is_secret_path(path):
            files.append(path)
    return sorted(files)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def load_pyproject(repo: Path) -> dict[str, Any]:
    path = repo / "pyproject.toml"
    if not path.is_file():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return {}


def path_id(prefix: str, rel: str, name: str = "") -> str:
    raw = f"{prefix}:{rel}:{name}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}:{digest}"


def relpath(repo: Path, path: Path) -> str:
    return path.resolve().relative_to(repo.resolve()).as_posix()


def module_name_from_path(rel: str) -> str:
    if rel.endswith("/__init__.py"):
        rel = rel[: -len("/__init__.py")]
    elif rel.endswith(".py"):
        rel = rel[:-3]
    return rel.replace("/", ".")


def evidence(rel: str, line: int | str) -> list[str]:
    return [f"{rel}:{line}"]


def safe_json_load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def analyzer_dirs(repo: Path) -> None:
    for rel in [
        ".analyzer",
        ".analyzer/semantic-cache",
        ".analyzer/snapshots",
        ".analyzer/diff-overlays",
        ".analyzer/reports",
        ".analyzer/schemas",
    ]:
        (repo / rel).mkdir(parents=True, exist_ok=True)


def imports_from_ast(tree: ast.AST) -> list[tuple[str, int]]:
    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append((node.module, node.lineno))
    return imports


def env_names_from_ast(tree: ast.AST) -> list[tuple[str, int]]:
    names: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_environ_get = (
            isinstance(func, ast.Attribute)
            and func.attr == "get"
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == "environ"
            and isinstance(func.value.value, ast.Name)
            and func.value.value.id == "os"
        )
        is_getenv = (
            isinstance(func, ast.Attribute)
            and func.attr == "getenv"
            and isinstance(func.value, ast.Name)
            and func.value.id == "os"
        )
        if not (is_environ_get or is_getenv) or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            names.append((first.value, node.lineno))
    return names


def call_names_from_ast(tree: ast.AST) -> list[tuple[str, int]]:
    calls: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            calls.append((func.id, node.lineno))
        elif isinstance(func, ast.Attribute):
            calls.append((func.attr, node.lineno))
    return calls


def has_ambiguous_task(task: str) -> bool:
    lowered = task.lower()
    if "somehow" in lowered:
        return True
    ambiguous_markers = ["somehow", "make it better", "improve", "enhance", "fix stuff"]
    concrete_markers = [".py", "/", " timeout", " error", " validation", " provider", " cli"]
    return any(marker in lowered for marker in ambiguous_markers) and not any(
        marker in lowered for marker in concrete_markers
    )


def default_upper_bound_checks() -> list[dict[str, Any]]:
    return [
        {
            "check": "dirty worktree handling",
            "reason": "Action agents may start from uncommitted state.",
        },
        {
            "check": "malformed Action Packet rejection",
            "reason": "Critics must verify packet boundaries before accepting work.",
        },
        {
            "check": "forbidden file modification detection",
            "reason": "Analyzer output constrains action-agent scope.",
        },
        {
            "check": "user-visible CLI output and exit-code behavior",
            "reason": "CLI regressions can pass unit tests but fail users.",
        },
    ]


def extract_file_mentions(task: str, repo: Path) -> list[str]:
    mentions = sorted(set(re.findall(r"[\w./-]+\.py", task)))
    existing = [mention for mention in mentions if (repo / mention).is_file()]
    if existing:
        return existing
    lowered = task.lower()
    inferred: list[str] = []
    for file_path in iter_repo_files(repo):
        rel = relpath(repo, file_path)
        if file_path.suffix == ".py" and any(part in lowered for part in Path(rel).parts):
            inferred.append(rel)
    return sorted(set(inferred))
