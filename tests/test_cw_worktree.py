from __future__ import annotations

import importlib.util
from pathlib import Path


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("cw_worktree", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_worker_branch_name_uses_task_slug_then_feature() -> None:
    module = load_module(Path("composer/bin/worktree.py"))

    assert module.worker_branch("architecture", "checkout") == "architecture/checkout"
    assert module.worker_branch("api-design", "checkout-v2") == "api-design/checkout-v2"


def test_slugs_reject_branch_traversal() -> None:
    module = load_module(Path("composer/bin/worktree.py"))

    assert module.validate_slug("checkout-v2") == []
    assert "must not contain '..'" in module.validate_slug("../checkout")[0]
    assert "must use letters, digits, '.', '_' or '-'" in module.validate_slug("bad slug")[0]
