from __future__ import annotations

import json
from pathlib import Path


REQUIRED_REFERENCES = [
    "graph-schema.md",
    "repository-survey.md",
    "static-analysis.md",
    "semantic-enrichment.md",
    "architecture-layering.md",
    "interface-contracts.md",
    "impact-analysis.md",
    "task-decomposition.md",
    "test-gap-analysis.md",
    "upper-bound-tests.md",
    "evidence-and-confidence.md",
    "output-contract.md",
]


REQUIRED_SCRIPTS = [
    "collect_repository_facts.py",
    "build_static_graph.py",
    "compute_diff_impact.py",
    "validate_graph.py",
    "validate_analysis_result.py",
]


def test_analyser_plugin_manifest_and_skill_layout() -> None:
    manifest = json.loads(
        Path("analyser/.codex-plugin/plugin.json").read_text(encoding="utf-8")
    )
    skill = Path("skills/analyze/SKILL.md").read_text(encoding="utf-8")

    assert manifest["name"] == "analyser"
    assert manifest["skills"] == "./skills"
    assert "repository intelligence and task-specification layer" in skill
    assert "not generic code summarization" in skill
    assert "Stage A" in skill and "Stage G" in skill
    assert "Action Packet" in skill
    assert "Critic Review" in skill
    assert "Do not edit application feature code" in skill


def test_analyser_skill_folder_matches_command_name() -> None:
    assert Path("skills/analyze/SKILL.md").is_file()
    assert not Path("skills/analyzer").exists()
    assert not Path("skills/aac-analyzer").exists()


def test_analyser_required_references_and_scripts_exist() -> None:
    root = Path("skills/analyze")

    for reference in REQUIRED_REFERENCES:
        assert (root / "references" / reference).is_file()
    for script in REQUIRED_SCRIPTS:
        assert (root / "scripts" / script).is_file()


def test_output_contract_contains_required_top_level_keys() -> None:
    contract = Path(
        "skills/analyze/references/output-contract.md"
    ).read_text(encoding="utf-8")

    for key in [
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
    ]:
        assert key in contract


def test_task_decomposition_reuses_action_packet_and_critic_review_terms() -> None:
    reference = Path(
        "skills/analyze/references/task-decomposition.md"
    ).read_text(encoding="utf-8")

    assert "Action Packet" in reference
    assert "Critic Review" in reference
    assert "Do not create a second packet schema" in reference
