from __future__ import annotations

from pathlib import Path


def test_analyser_uses_analyze_command_not_analyse() -> None:
    command_dir = Path("plugins/analyser/commands")

    assert (command_dir / "analyze.md").is_file()
    assert not (command_dir / "analyse.md").exists()

    body = (command_dir / "analyze.md").read_text(encoding="utf-8")
    assert "Analyze a repository task" in body
    assert "`$ARGUMENTS`" in body
