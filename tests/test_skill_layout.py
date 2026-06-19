from __future__ import annotations

import json
from pathlib import Path


def test_composer_skill_folder_matches_command_name() -> None:
    assert Path("skills/compose/SKILL.md").is_file()
    assert not Path("skills/SKILL.md").exists()


def test_analyser_skill_folder_matches_command_name() -> None:
    assert Path("skills/analyze/SKILL.md").is_file()
    assert not Path("skills/analyzer").exists()
    assert not Path("skills/aac-analyzer").exists()


def test_plugins_are_top_level_for_claude_code_plugin_discovery() -> None:
    assert Path("composer/.claude-plugin/plugin.json").is_file()
    assert Path("analyser/.claude-plugin/plugin.json").is_file()
    assert not Path("plugins").exists()


def test_claude_plugin_manifests_use_current_schema() -> None:
    for plugin in ("composer", "analyser"):
        manifest = json.loads(
            Path(plugin, ".claude-plugin", "plugin.json").read_text(encoding="utf-8")
        )

        assert isinstance(manifest["skills"], list)
        assert "agents" not in manifest
