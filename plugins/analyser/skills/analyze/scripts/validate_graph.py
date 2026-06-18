#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_GRAPH_KEYS = {"graph_version", "source_commit", "nodes", "edges"}
REQUIRED_NODE_KEYS = {"id", "kind", "name", "evidence", "confidence"}
REQUIRED_EDGE_KEYS = {"source", "target", "kind", "confidence", "evidence"}


def validate_graph(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    missing = sorted(REQUIRED_GRAPH_KEYS - set(payload))
    for key in missing:
        errors.append(f"missing graph key: {key}")
    if not isinstance(payload.get("nodes"), list):
        errors.append("nodes must be a list")
    if not isinstance(payload.get("edges"), list):
        errors.append("edges must be a list")

    node_ids = set()
    for index, node in enumerate(payload.get("nodes", [])):
        if not isinstance(node, dict):
            errors.append(f"node {index} must be an object")
            continue
        for key in sorted(REQUIRED_NODE_KEYS - set(node)):
            errors.append(f"node {index} missing key: {key}")
        if node.get("id") in node_ids:
            errors.append(f"duplicate node id: {node.get('id')}")
        node_ids.add(node.get("id"))

    for index, edge in enumerate(payload.get("edges", [])):
        if not isinstance(edge, dict):
            errors.append(f"edge {index} must be an object")
            continue
        for key in sorted(REQUIRED_EDGE_KEYS - set(edge)):
            errors.append(f"edge {index} missing key: {key}")
        if edge.get("source") not in node_ids:
            errors.append(f"edge {index} has unknown source: {edge.get('source')}")
        if edge.get("target") not in node_ids:
            errors.append(f"edge {index} has unknown target: {edge.get('target')}")

    serialized = json.dumps(payload)
    if "must-not-leak" in serialized:
        errors.append("graph contains fixture secret value")

    return {"valid": not errors, "errors": errors}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate analyzer graph JSON.")
    parser.add_argument("graph_path", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        payload = json.loads(args.graph_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, indent=2, sort_keys=True))
        return
    print(json.dumps(validate_graph(payload), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
