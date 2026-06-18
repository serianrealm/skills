from __future__ import annotations

import json
from pathlib import Path


def test_plugin_is_named_composer() -> None:
    claude_manifest = json.loads(
        Path("plugins/composer/.claude-plugin/plugin.json").read_text(encoding="utf-8")
    )
    codex_manifest = json.loads(
        Path("plugins/composer/.codex-plugin/plugin.json").read_text(encoding="utf-8")
    )

    assert claude_manifest["name"] == "composer"
    assert codex_manifest["name"] == "composer"
    assert codex_manifest["interface"]["displayName"] == "Composer"


def test_hooks_point_to_composer_install_path() -> None:
    hooks = Path("plugins/composer/hooks/hooks.json").read_text(encoding="utf-8")

    assert "$HOME/.claude/skills/composer/bin/guard.py" in hooks
    assert "$HOME/.claude/skills/handoff" not in hooks
