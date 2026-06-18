from __future__ import annotations

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
