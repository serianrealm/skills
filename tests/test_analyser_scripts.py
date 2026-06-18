from __future__ import annotations

import json
import subprocess
from pathlib import Path


SCRIPT_ROOT = Path("skills/analyze/scripts")


def run_json(args: list[str], cwd: Path | None = None) -> dict:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def make_fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "fixture"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        """
[project]
name = "fixture"
dependencies = ["click"]

[project.scripts]
fixture = "fixture.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (repo / "fixture").mkdir()
    (repo / "fixture" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "fixture" / "cli.py").write_text(
        """
import argparse
import os

from fixture.provider import launch_provider

PUBLIC_TIMEOUT = int(os.environ.get("FIXTURE_TIMEOUT", "30"))


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return launch_provider(args.provider)
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (repo / "fixture" / "provider.py").write_text(
        """
class ProviderLauncher:
    def launch(self, provider):
        return provider or "default"


def launch_provider(provider):
    launcher = ProviderLauncher()
    return launcher.launch(provider)
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (repo / "tests").mkdir()
    (repo / "tests" / "test_cli.py").write_text(
        """
from fixture.cli import main


def test_main_uses_default_provider():
    assert main([]) == "default"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (repo / ".env").write_text("SECRET_TOKEN=must-not-leak\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "fixture"],
        cwd=repo,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return repo


def test_collect_repository_facts_detects_commands_and_avoids_secret_values(tmp_path: Path) -> None:
    repo = make_fixture_repo(tmp_path)

    facts = run_json(
        [
            "python3",
            str(SCRIPT_ROOT / "collect_repository_facts.py"),
            "--repo",
            str(repo),
        ]
    )

    assert facts["repository_snapshot"]["repository_root"] == str(repo.resolve())
    assert "Python" in facts["repository_facts"]["languages"]
    assert "pyproject.toml" in facts["repository_facts"]["package_managers"]
    assert any("pytest" in command for command in facts["repository_facts"]["test_commands"])
    assert any(entry["name"] == "fixture" for entry in facts["repository_facts"]["entry_points"])
    assert "FIXTURE_TIMEOUT" in facts["repository_facts"]["environment_variables"]
    assert "must-not-leak" not in json.dumps(facts)


def test_build_static_graph_generates_cached_graph_and_reuses_commit(tmp_path: Path) -> None:
    repo = make_fixture_repo(tmp_path)

    first = run_json(
        [
            "python3",
            str(SCRIPT_ROOT / "build_static_graph.py"),
            "--repo",
            str(repo),
            "--write",
        ]
    )
    second = run_json(
        [
            "python3",
            str(SCRIPT_ROOT / "build_static_graph.py"),
            "--repo",
            str(repo),
            "--write",
        ]
    )

    assert first["project_graph"]["artifact_path"] == ".analyzer/graph.json"
    assert first["project_graph"]["stale"] is False
    assert second["cache"]["reused"] is True
    graph = json.loads((repo / ".analyzer" / "graph.json").read_text(encoding="utf-8"))
    node_kinds = {node["kind"] for node in graph["nodes"]}
    edge_kinds = {edge["kind"] for edge in graph["edges"]}
    assert {"file", "function", "class", "environment_variable"} <= node_kinds
    assert "imports" in edge_kinds
    assert "SECRET_TOKEN" not in json.dumps(graph)


def test_graph_validation_and_dependency_path(tmp_path: Path) -> None:
    repo = make_fixture_repo(tmp_path)
    run_json(
        [
            "python3",
            str(SCRIPT_ROOT / "build_static_graph.py"),
            "--repo",
            str(repo),
            "--write",
        ]
    )

    validation = run_json(
        [
            "python3",
            str(SCRIPT_ROOT / "validate_graph.py"),
            str(repo / ".analyzer" / "graph.json"),
        ]
    )
    impact = run_json(
        [
            "python3",
            str(SCRIPT_ROOT / "compute_diff_impact.py"),
            "--repo",
            str(repo),
            "--query",
            "What path connects this CLI command to the provider launcher?",
            "--task",
            "Add provider timeout handling",
        ]
    )

    assert validation["valid"] is True
    assert impact["impact_analysis"]["dependency_paths"]
    assert any(
        "fixture.cli" in " ".join(path["path"]) and "fixture.provider" in " ".join(path["path"])
        for path in impact["impact_analysis"]["dependency_paths"]
    )


def test_analysis_result_ready_blocked_packets_upper_bounds_and_validation(tmp_path: Path) -> None:
    repo = make_fixture_repo(tmp_path)
    run_json(
        [
            "python3",
            str(SCRIPT_ROOT / "build_static_graph.py"),
            "--repo",
            str(repo),
            "--write",
        ]
    )

    ready = run_json(
        [
            "python3",
            str(SCRIPT_ROOT / "compute_diff_impact.py"),
            "--repo",
            str(repo),
            "--task",
            "Add provider timeout handling in fixture/cli.py and fixture/provider.py",
        ]
    )
    blocked = run_json(
        [
            "python3",
            str(SCRIPT_ROOT / "compute_diff_impact.py"),
            "--repo",
            str(repo),
            "--task",
            "Improve the provider integration somehow",
        ]
    )

    assert ready["analysis_result"]["status"] == "ready"
    assert len(ready["action_plan"]["packets"]) >= 2
    allowed_sets = [set(packet["allowed_files"]) for packet in ready["action_plan"]["packets"]]
    assert allowed_sets[0].isdisjoint(allowed_sets[1])
    assert ready["test_plan"]["upper_bound_checks"]
    assert blocked["analysis_result"]["status"] == "blocked"
    assert blocked["recommended_next_step"] == "ask_user"
    assert blocked["requirement_interpretation"]["open_questions"]

    validation = run_json(
        [
            "python3",
            str(Path.cwd() / SCRIPT_ROOT / "validate_analysis_result.py"),
            "--input",
            "-",
        ],
        cwd=repo,
    )
    assert validation["valid"] is False

    proc = subprocess.run(
        [
            "python3",
            str((Path.cwd() / SCRIPT_ROOT / "validate_analysis_result.py")),
            "--input",
            "-",
        ],
        cwd=repo,
        input=json.dumps(ready),
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(proc.stdout)["valid"] is True
