from __future__ import annotations

from pathlib import Path


def test_composer_skill_folder_matches_command_name() -> None:
    assert Path("plugins/composer/skills/compose/SKILL.md").is_file()
    assert not Path("plugins/composer/skills/SKILL.md").exists()


def test_analyser_skill_folder_matches_command_name() -> None:
    assert Path("plugins/analyser/skills/analyze/SKILL.md").is_file()
    assert not Path("plugins/analyser/skills/analyzer").exists()
    assert not Path("plugins/analyser/skills/aac-analyzer").exists()
