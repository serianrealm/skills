# Static Analysis

Prefer deterministic analysis:

- Python AST for modules, imports, classes, functions, methods, calls, argparse flags, and env var names.
- Manifest parsing for dependencies and entry points.
- File-system structure for directories, tests, generated artifacts, and config files.
- Grep only for targeted, non-secret patterns.

Gracefully degrade when no parser exists. Emit low-confidence findings with caveats instead of inventing relationships.
