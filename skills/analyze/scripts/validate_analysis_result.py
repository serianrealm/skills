#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_KEYS = {
    "analysis_result",
    "repository_snapshot",
    "repository_facts",
    "project_graph",
    "architecture",
    "requirement_interpretation",
    "impact_analysis",
    "action_plan",
    "test_plan",
    "evidence",
    "recommended_next_step",
}
VALID_STATUSES = {"ready", "blocked", "stale", "failed"}
VALID_NEXT_STEPS = {"ask_user", "spawn_actions", "stop"}


def validate_analysis_result(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    for key in sorted(REQUIRED_KEYS - set(payload)):
        errors.append(f"missing top-level key: {key}")
    status = payload.get("analysis_result", {}).get("status")
    if status not in VALID_STATUSES:
        errors.append("analysis_result.status must be ready, blocked, stale, or failed")
    if payload.get("recommended_next_step") not in VALID_NEXT_STEPS:
        errors.append("recommended_next_step is invalid")
    claims = payload.get("evidence", {}).get("claims", [])
    if not isinstance(claims, list):
        errors.append("evidence.claims must be a list")
    else:
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict):
                errors.append(f"claim {index} must be an object")
                continue
            for key in ["text", "type", "confidence", "evidence"]:
                if key not in claim:
                    errors.append(f"claim {index} missing key: {key}")
    if status == "ready" and not payload.get("action_plan", {}).get("packets"):
        errors.append("ready results must contain Action Packets")
    if status == "blocked" and not payload.get("requirement_interpretation", {}).get("open_questions"):
        errors.append("blocked results must contain open questions")
    serialized = json.dumps(payload)
    if "must-not-leak" in serialized:
        errors.append("analysis result contains fixture secret value")
    return {"valid": not errors, "errors": errors}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate analyzer output contract.")
    parser.add_argument("--input", required=True, help="Path to JSON result or '-' for stdin")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    if not raw.strip():
        print(json.dumps({"valid": False, "errors": ["empty input"]}, indent=2, sort_keys=True))
        return
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, indent=2, sort_keys=True))
        return
    print(json.dumps(validate_analysis_result(payload), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
