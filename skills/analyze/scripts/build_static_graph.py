#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

from analyzer_common import (
    GRAPH_VERSION,
    analyzer_dirs,
    call_names_from_ast,
    env_names_from_ast,
    evidence,
    imports_from_ast,
    iter_repo_files,
    load_pyproject,
    module_name_from_path,
    path_id,
    read_text,
    relpath,
    repo_root,
    repository_snapshot,
    safe_json_load,
    utc_now,
)


def build_static_graph(repo: Path, *, write: bool = False) -> dict[str, Any]:
    repo = repo_root(repo)
    snapshot = repository_snapshot(repo)
    analyzer_root = repo / ".analyzer"
    graph_path = analyzer_root / "graph.json"
    meta_path = analyzer_root / "graph.meta.json"
    existing_meta = safe_json_load(meta_path)
    if write and graph_path.is_file() and existing_meta.get("source_commit") == snapshot["commit"]:
        existing = safe_json_load(graph_path)
        if existing.get("graph_version") == GRAPH_VERSION:
            return {
                "project_graph": {
                    "artifact_path": ".analyzer/graph.json",
                    "graph_version": GRAPH_VERSION,
                    "source_commit": snapshot["commit"],
                    "stale": False,
                    "nodes": existing.get("nodes", []),
                    "edges": existing.get("edges", []),
                },
                "cache": {"reused": True, "reason": "source commit unchanged"},
            }

    graph = _build_graph_payload(repo, snapshot)
    if write:
        analyzer_dirs(repo)
        graph_path.write_text(json.dumps(graph, indent=2, sort_keys=True), encoding="utf-8")
        meta_path.write_text(
            json.dumps(
                {
                    "graph_version": GRAPH_VERSION,
                    "source_commit": snapshot["commit"],
                    "repository_root": str(repo),
                    "generated_at": graph["generated_at"],
                    "dirty": snapshot["dirty"],
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    return {
        "project_graph": {
            "artifact_path": ".analyzer/graph.json",
            "graph_version": GRAPH_VERSION,
            "source_commit": snapshot["commit"],
            "stale": False,
            "nodes": graph["nodes"],
            "edges": graph["edges"],
        },
        "cache": {"reused": False, "reason": "graph rebuilt"},
    }


def _build_graph_payload(repo: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    node_by_module: dict[str, str] = {}
    node_by_function: dict[str, str] = {}
    file_node_by_rel: dict[str, str] = {}

    for directory in sorted({path.parent for path in iter_repo_files(repo)}):
        rel = "." if directory == repo else relpath(repo, directory)
        nodes.append(
            {
                "id": path_id("dir", rel),
                "kind": "directory",
                "path": rel,
                "name": rel,
                "evidence": [rel],
                "confidence": "high",
                "metadata": {},
            }
        )

    pyproject = load_pyproject(repo)
    dependencies = pyproject.get("project", {}).get("dependencies", [])
    for dependency in dependencies:
        name = str(dependency).split()[0]
        nodes.append(
            {
                "id": path_id("dep", name),
                "kind": "external_dependency",
                "path": "pyproject.toml",
                "name": name,
                "evidence": ["pyproject.toml:project.dependencies"],
                "confidence": "high",
                "metadata": {},
            }
        )

    scripts = pyproject.get("project", {}).get("scripts", {})
    for command, target in sorted(scripts.items()):
        nodes.append(
            {
                "id": path_id("cli", command),
                "kind": "cli_command",
                "path": "pyproject.toml",
                "name": command,
                "evidence": ["pyproject.toml:project.scripts"],
                "confidence": "high",
                "metadata": {"target": target},
            }
        )

    for path in iter_repo_files(repo):
        rel = relpath(repo, path)
        file_id = path_id("file", rel)
        file_node_by_rel[rel] = file_id
        kind = "test_file" if _is_test_file(rel) else "file"
        nodes.append(
            {
                "id": file_id,
                "kind": kind,
                "path": rel,
                "name": path.name,
                "language": "Python" if path.suffix == ".py" else None,
                "evidence": [rel],
                "confidence": "high",
                "metadata": {},
            }
        )
        if path.suffix != ".py":
            continue

        module_name = module_name_from_path(rel)
        module_id = path_id("module", rel, module_name)
        node_by_module[module_name] = module_id
        nodes.append(
            {
                "id": module_id,
                "kind": "module",
                "path": rel,
                "name": module_name,
                "language": "Python",
                "evidence": [rel],
                "confidence": "high",
                "metadata": _semantic_metadata_for_path(rel, module_name),
            }
        )
        edges.append(
            {
                "source": file_id,
                "target": module_id,
                "kind": "contains",
                "confidence": "high",
                "evidence": [rel],
            }
        )
        try:
            tree = ast.parse(read_text(path))
        except SyntaxError:
            continue

        imported_modules = imports_from_ast(tree)
        for imported, line in imported_modules:
            import_id = path_id("import", rel, imported)
            nodes.append(
                {
                    "id": import_id,
                    "kind": "import",
                    "path": rel,
                    "name": imported,
                    "evidence": evidence(rel, line),
                    "confidence": "high",
                    "metadata": {},
                }
            )
            edges.append(
                {
                    "source": module_id,
                    "target": import_id,
                    "kind": "imports",
                    "confidence": "high",
                    "evidence": evidence(rel, line),
                }
            )

        for env_name, line in env_names_from_ast(tree):
            env_id = path_id("env", env_name)
            nodes.append(
                {
                    "id": env_id,
                    "kind": "environment_variable",
                    "path": rel,
                    "name": env_name,
                    "evidence": evidence(rel, line),
                    "confidence": "high",
                    "metadata": {},
                }
            )
            edges.append(
                {
                    "source": module_id,
                    "target": env_id,
                    "kind": "config_flow",
                    "confidence": "high",
                    "evidence": evidence(rel, line),
                }
            )

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_id = path_id("class", rel, node.name)
                nodes.append(
                    {
                        "id": class_id,
                        "kind": "class",
                        "path": rel,
                        "name": node.name,
                        "evidence": evidence(rel, node.lineno),
                        "confidence": "high",
                        "metadata": {
                            "public": not node.name.startswith("_"),
                            **_semantic_metadata_for_path(rel, node.name),
                        },
                    }
                )
                edges.append(
                    {
                        "source": module_id,
                        "target": class_id,
                        "kind": "contains",
                        "confidence": "high",
                        "evidence": evidence(rel, node.lineno),
                    }
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_id = path_id("function", rel, node.name)
                node_by_function[f"{module_name}.{node.name}"] = function_id
                nodes.append(
                    {
                        "id": function_id,
                        "kind": "function",
                        "path": rel,
                        "name": node.name,
                        "evidence": evidence(rel, node.lineno),
                        "confidence": "high",
                        "metadata": {
                            "public": not node.name.startswith("_"),
                            **_semantic_metadata_for_path(rel, node.name),
                        },
                    }
                )
                edges.append(
                    {
                        "source": module_id,
                        "target": function_id,
                        "kind": "contains",
                        "confidence": "high",
                        "evidence": evidence(rel, node.lineno),
                    }
                )

        for call_name, line in call_names_from_ast(tree):
            target_id = _find_function_id(call_name, node_by_function)
            if target_id:
                edges.append(
                    {
                        "source": module_id,
                        "target": target_id,
                        "kind": "calls",
                        "confidence": "medium",
                        "evidence": evidence(rel, line),
                        "caveat": "Static call target matched by local function name.",
                    }
                )

    _link_import_targets(edges, nodes, node_by_module)
    _link_cli_targets(edges, nodes, node_by_module)
    _link_tests(edges, nodes, file_node_by_rel)
    return {
        "graph_version": GRAPH_VERSION,
        "source_commit": snapshot["commit"],
        "generated_at": utc_now(),
        "repository_root": str(repo),
        "nodes": _dedupe_nodes(nodes),
        "edges": _dedupe_edges(edges),
    }


def _find_function_id(name: str, node_by_function: dict[str, str]) -> str | None:
    matches = [node_id for qualified, node_id in node_by_function.items() if qualified.endswith(f".{name}")]
    if len(matches) == 1:
        return matches[0]
    return None


def _link_import_targets(edges: list[dict[str, Any]], nodes: list[dict[str, Any]], node_by_module: dict[str, str]) -> None:
    import_nodes = [node for node in nodes if node["kind"] == "import"]
    for node in import_nodes:
        imported = node["name"]
        target = node_by_module.get(imported)
        if target:
            edges.append(
                {
                    "source": node["id"],
                    "target": target,
                    "kind": "resolves_to",
                    "confidence": "high",
                    "evidence": node["evidence"],
                }
            )


def _link_cli_targets(edges: list[dict[str, Any]], nodes: list[dict[str, Any]], node_by_module: dict[str, str]) -> None:
    for node in nodes:
        if node["kind"] != "cli_command":
            continue
        target = str(node.get("metadata", {}).get("target", ""))
        module = target.split(":", 1)[0]
        target_id = node_by_module.get(module)
        if target_id:
            edges.append(
                {
                    "source": node["id"],
                    "target": target_id,
                    "kind": "cli_dispatch",
                    "confidence": "high",
                    "evidence": node["evidence"],
                }
            )


def _link_tests(edges: list[dict[str, Any]], nodes: list[dict[str, Any]], file_node_by_rel: dict[str, str]) -> None:
    files_by_stem = {Path(rel).stem.replace("test_", ""): node_id for rel, node_id in file_node_by_rel.items()}
    for node in nodes:
        if node["kind"] != "test_file":
            continue
        stem = Path(node["path"]).stem.replace("test_", "")
        target = files_by_stem.get(stem)
        if target and target != node["id"]:
            edges.append(
                {
                    "source": node["id"],
                    "target": target,
                    "kind": "tests",
                    "confidence": "medium",
                    "evidence": node["evidence"],
                    "caveat": "Matched by test file naming convention.",
                }
            )


def _semantic_metadata_for_path(rel: str, name: str) -> dict[str, Any]:
    lowered = f"{rel} {name}".lower()
    layer = "utilities"
    if "cli" in lowered or "command" in lowered:
        layer = "CLI / user interface"
    elif "config" in lowered or "settings" in lowered:
        layer = "configuration"
    elif "workflow" in lowered or "agent" in lowered:
        layer = "workflow orchestration"
    elif "provider" in lowered or "model" in lowered:
        layer = "provider or model routing"
    elif "git" in lowered or "worktree" in lowered or "branch" in lowered:
        layer = "Git / worktree management"
    elif "test" in lowered:
        layer = "tests"
    return {
        "architecture_layer": layer,
        "semantic_confidence": "medium" if layer != "utilities" else "low",
        "semantic_caveat": "Layer inferred from path and symbol names.",
    }


def _is_test_file(rel: str) -> bool:
    return "/tests/" in f"/{rel}" or Path(rel).name.startswith("test_") or Path(rel).name.endswith("_test.py")


def _dedupe_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for node in nodes:
        by_id.setdefault(node["id"], node)
    return list(by_id.values())


def _dedupe_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[dict[str, Any]] = []
    for edge in edges:
        key = (edge["source"], edge["target"], edge["kind"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(edge)
    return unique


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a deterministic static repository graph.")
    parser.add_argument("--repo", default=".", type=Path)
    parser.add_argument("--write", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(json.dumps(build_static_graph(args.repo, write=args.write), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
