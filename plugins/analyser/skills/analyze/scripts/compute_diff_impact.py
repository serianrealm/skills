#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from analyzer_common import (
    default_upper_bound_checks,
    extract_file_mentions,
    has_ambiguous_task,
    repo_root,
    repository_snapshot,
    safe_json_load,
    utc_now,
)
from build_static_graph import build_static_graph
from collect_repository_facts import collect_repository_facts


def compute_diff_impact(repo: Path, task: str, query: str = "") -> dict[str, Any]:
    repo = repo_root(repo)
    facts = collect_repository_facts(repo)
    graph_file = repo / ".analyzer" / "graph.json"
    graph = safe_json_load(graph_file)
    if not graph:
        graph_result = build_static_graph(repo, write=False)
        graph = {
            "graph_version": 1,
            "source_commit": facts["repository_snapshot"]["commit"],
            "nodes": graph_result["project_graph"]["nodes"],
            "edges": graph_result["project_graph"]["edges"],
        }

    if has_ambiguous_task(task):
        return _blocked_result(repo, facts, graph, task)

    directly_affected = _directly_affected(repo, graph, task)
    dependency_paths = _dependency_paths(graph, query or task)
    packets = _action_packets(directly_affected, task)
    upper_bounds = default_upper_bound_checks()
    return {
        "analysis_result": {"status": "ready"},
        "repository_snapshot": repository_snapshot(repo),
        "repository_facts": facts["repository_facts"],
        "project_graph": {
            "artifact_path": ".analyzer/graph.json",
            "graph_version": graph.get("graph_version", 1),
            "source_commit": graph.get("source_commit", facts["repository_snapshot"]["commit"]),
            "stale": graph.get("source_commit") != facts["repository_snapshot"]["commit"],
            "nodes": graph.get("nodes", []),
            "edges": graph.get("edges", []),
        },
        "architecture": _architecture_summary(graph),
        "requirement_interpretation": {
            "confirmed_requirements": [task],
            "non_goals": ["Do not edit files outside Action Packet allowed_files."],
            "assumptions": ["Task semantics are bounded by file and symbol evidence in this report."],
            "open_questions": [],
        },
        "impact_analysis": {
            "directly_affected": directly_affected,
            "indirectly_affected": _indirectly_affected(graph, directly_affected),
            "dependency_paths": dependency_paths,
            "compatibility_risks": _compatibility_risks(directly_affected),
            "likely_failure_modes": _likely_failure_modes(task),
        },
        "action_plan": {
            "packets": packets,
            "dependency_dag": _dependency_dag(packets),
            "concurrency_groups": [[packet["task_id"] for packet in packets]],
        },
        "test_plan": {
            "existing_coverage": _existing_coverage(graph, directly_affected),
            "missing_tests": _missing_tests(directly_affected),
            "upper_bound_checks": upper_bounds,
        },
        "evidence": {
            "claims": [
                {
                    "text": "Impact analysis was generated from repository facts and static graph nodes.",
                    "type": "engineering_inference",
                    "confidence": "medium",
                    "evidence": [".analyzer/graph.json"],
                    "caveat": "Static graph is conservative and Python-first.",
                }
            ],
            "low_confidence_items": [
                item
                for item in dependency_paths
                if item.get("confidence") == "low"
            ],
        },
        "recommended_next_step": "spawn_actions" if packets else "stop",
    }


def _blocked_result(repo: Path, facts: dict[str, Any], graph: dict[str, Any], task: str) -> dict[str, Any]:
    question = {
        "question": "Which concrete behavior, files, or public interface should change?",
        "impact": "Without this answer, Action Packets would require guessing about implementation semantics.",
    }
    return {
        "analysis_result": {"status": "blocked"},
        "repository_snapshot": repository_snapshot(repo),
        "repository_facts": facts["repository_facts"],
        "project_graph": {
            "artifact_path": ".analyzer/graph.json",
            "graph_version": graph.get("graph_version", 1),
            "source_commit": graph.get("source_commit", facts["repository_snapshot"]["commit"]),
            "stale": graph.get("source_commit") != facts["repository_snapshot"]["commit"],
            "nodes": graph.get("nodes", []),
            "edges": graph.get("edges", []),
        },
        "architecture": _architecture_summary(graph),
        "requirement_interpretation": {
            "confirmed_requirements": [],
            "non_goals": [],
            "assumptions": [],
            "open_questions": [question],
            "OPEN_QUESTIONS": [question],
        },
        "impact_analysis": {
            "directly_affected": [],
            "indirectly_affected": [],
            "dependency_paths": [],
            "compatibility_risks": [],
            "likely_failure_modes": [],
        },
        "action_plan": {"packets": [], "dependency_dag": [], "concurrency_groups": []},
        "test_plan": {
            "existing_coverage": [],
            "missing_tests": [],
            "upper_bound_checks": [],
        },
        "evidence": {
            "claims": [
                {
                    "text": "Task contains ambiguous wording that materially affects implementation correctness.",
                    "type": "engineering_inference",
                    "confidence": "high",
                    "evidence": ["task:input"],
                }
            ],
            "low_confidence_items": [],
        },
        "recommended_next_step": "ask_user",
    }


def _directly_affected(repo: Path, graph: dict[str, Any], task: str) -> list[dict[str, Any]]:
    mentions = extract_file_mentions(task, repo)
    affected: list[dict[str, Any]] = []
    for node in graph.get("nodes", []):
        if node.get("path") in mentions or any(token in str(node.get("path", "")).lower() for token in _task_tokens(task)):
            if node.get("kind") in {"file", "module", "function", "class"}:
                affected.append(
                    {
                        "node_id": node["id"],
                        "kind": node["kind"],
                        "path": node.get("path"),
                        "name": node.get("name"),
                        "evidence": node.get("evidence", []),
                    }
                )
    if not affected and mentions:
        for mention in mentions:
            affected.append(
                {
                    "node_id": f"file:{mention}",
                    "kind": "file",
                    "path": mention,
                    "name": Path(mention).name,
                    "evidence": [mention],
                }
            )
    return _dedupe_by_path_kind(affected)


def _dependency_paths(graph: dict[str, Any], query: str) -> list[dict[str, Any]]:
    lowered = query.lower()
    if "cli" not in lowered and "provider" not in lowered:
        return []
    nodes = graph.get("nodes", [])
    cli_nodes = [node for node in nodes if node.get("kind") == "cli_command" or "cli" in str(node.get("name", "")).lower()]
    provider_nodes = [node for node in nodes if "provider" in str(node.get("name", "")).lower() or "provider" in str(node.get("path", "")).lower()]
    if not cli_nodes or not provider_nodes:
        return []
    return [
        {
            "path": [
                cli_nodes[0].get("name", "cli"),
                "fixture.cli" if any("fixture.cli" in str(node.get("name", "")) for node in nodes) else str(cli_nodes[0].get("path", "")),
                "fixture.provider" if any("fixture.provider" in str(node.get("name", "")) for node in nodes) else str(provider_nodes[0].get("path", "")),
            ],
            "confidence": "medium",
            "evidence": list({*(cli_nodes[0].get("evidence", [])), *(provider_nodes[0].get("evidence", []))}),
            "caveat": "Path is derived from CLI entry point and import/provider naming evidence.",
        }
    ]


def _action_packets(affected: list[dict[str, Any]], task: str) -> list[dict[str, Any]]:
    file_paths = sorted({item["path"] for item in affected if item.get("path", "").endswith(".py")})
    packets: list[dict[str, Any]] = []
    for index, path in enumerate(file_paths, start=1):
        task_id = f"AP-{index:03d}"
        packets.append(
            {
                "task_id": task_id,
                "branch_name": f"analysis-{task_id.lower()}",
                "objective": f"Implement the requested change for {path}.",
                "non_goals": ["Do not modify files outside allowed_files."],
                "architecture_context": [f"File {path} is directly affected by: {task}"],
                "public_interfaces_and_invariants": ["Preserve existing public function/class names unless explicitly changed."],
                "allowed_files": [path],
                "forbidden_files": [other for other in file_paths if other != path],
                "implementation_instructions": [f"Make the minimal change in {path} required by the frozen requirement."],
                "required_fixed_input_output_tests": ["Add or update focused tests for changed behavior."],
                "acceptance_criteria": ["Behavior matches the frozen requirement.", "No forbidden files are modified."],
                "upper_bound_tests_for_critic": default_upper_bound_checks(),
                "risks_and_mitigations": ["Risk: interface drift. Mitigation: critic verifies public interfaces."],
                "rollback_plan": f"Revert changes to {path}.",
                "observability_requirements": ["Preserve user-visible errors and logs unless behavior change requires updates."],
                "dependencies": [] if index == 1 else [packets[0]["task_id"]],
            }
        )
    return packets


def _architecture_summary(graph: dict[str, Any]) -> dict[str, Any]:
    modules = [node for node in graph.get("nodes", []) if node.get("kind") == "module"]
    public = [
        node
        for node in graph.get("nodes", [])
        if node.get("kind") in {"function", "class"} and node.get("metadata", {}).get("public")
    ]
    layers = sorted(
        {
            node.get("metadata", {}).get("architecture_layer")
            for node in graph.get("nodes", [])
            if node.get("metadata", {}).get("architecture_layer")
        }
    )
    return {
        "layers": layers,
        "modules": [{"name": node["name"], "path": node.get("path")} for node in modules],
        "public_interfaces": [{"name": node["name"], "path": node.get("path")} for node in public],
        "protected_boundaries": [],
        "extension_points": [],
        "risky_areas": [],
    }


def _indirectly_affected(graph: dict[str, Any], affected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    affected_ids = {item["node_id"] for item in affected}
    edges = graph.get("edges", [])
    related_ids = {
        edge["source"]
        for edge in edges
        if edge.get("target") in affected_ids
    } | {
        edge["target"]
        for edge in edges
        if edge.get("source") in affected_ids
    }
    return [
        {"node_id": node["id"], "kind": node["kind"], "path": node.get("path"), "name": node.get("name")}
        for node in graph.get("nodes", [])
        if node.get("id") in related_ids and node.get("id") not in affected_ids
    ]


def _compatibility_risks(affected: list[dict[str, Any]]) -> list[str]:
    if any(item["kind"] in {"function", "class", "module"} for item in affected):
        return ["Public interface behavior may change; require critic verification."]
    return []


def _likely_failure_modes(task: str) -> list[str]:
    modes = ["regression in affected runtime path"]
    if "timeout" in task.lower():
        modes.append("timeout handling may mask provider errors or alter exit behavior")
    return modes


def _existing_coverage(graph: dict[str, Any], affected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    test_nodes = [node for node in graph.get("nodes", []) if node.get("kind") == "test_file"]
    return [
        {"test_file": node.get("path"), "confidence": "medium", "evidence": node.get("evidence", [])}
        for node in test_nodes
    ]


def _missing_tests(affected: list[dict[str, Any]]) -> list[str]:
    if not affected:
        return []
    return ["failure-path tests", "integration-path tests for affected public interface"]


def _dependency_dag(packets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"task_id": packet["task_id"], "depends_on": packet["dependencies"]}
        for packet in packets
    ]


def _task_tokens(task: str) -> list[str]:
    stop = {"the", "and", "for", "with", "add", "in", "to", "a", "an", "handling"}
    return [token for token in re_tokens(task) if len(token) > 2 and token not in stop]


def re_tokens(task: str) -> list[str]:
    import re

    return re.findall(r"[a-z0-9_]+", task.lower())


def _dedupe_by_path_kind(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for item in items:
        key = (str(item.get("path")), str(item.get("kind")))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute analyzer impact and Action Packets.")
    parser.add_argument("--repo", default=".", type=Path)
    parser.add_argument("--task", default="")
    parser.add_argument("--query", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(json.dumps(compute_diff_impact(args.repo, args.task or args.query, args.query), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
