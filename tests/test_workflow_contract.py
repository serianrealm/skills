from __future__ import annotations

from pathlib import Path


def test_compose_skill_requires_changelog_and_docs_after_workers() -> None:
    body = Path("skills/compose/SKILL.md").read_text(encoding="utf-8")

    assert "After all worker branches are accepted and merged" in body
    assert "CHANGELOG.md" in body
    assert "document the additional features and implementations in `docs/**`" in body


def test_composer_agent_requires_final_documentation_loop() -> None:
    body = Path("composer/agents/composer.md").read_text(encoding="utf-8")

    assert "After every worker task is accepted and merged" in body
    assert "write `CHANGELOG.md`" in body
    assert "write the additional features and implementations into `docs/**`" in body
