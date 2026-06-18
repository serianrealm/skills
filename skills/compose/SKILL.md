---
name: compose
description: "Use when the user wants Claude Code automation with the Composer worker workflow: a composer analyzes a repository, writes ASSIGNMENT.md files, dispatches architecturer or developer workers on isolated git branches, requires HANDOFF.md completion, performs strict review, tests, runtime checks, merges worker branches into a feature branch, then updates CHANGELOG.md and docs."
---

# Composer Compose

Use this skill to run the Composer worker workflow inside a git repository.

## Roles

- `composer`: reads the full workspace, writes only `docs/**`, `.agents/**`, and root `CHANGELOG.md`, runs terminal commands, starts workers, reviews work, runs tests/runtime checks, merges branches, and records final documentation.
- `architecturer`: works on `architecture/<feature_name>`, writes src interfaces/frameworks and tests together, follows test-driven-development, and may own `docs/<feature_name>` if docs are needed.
- `developer`: works on `<task_slug>/<feature_name>`, implements src code only, and must not read, search, write, or run tests.

## Branches

- Keep `main` as the root branch.
- Create `<feature_name>` from `main`.
- Create worker branches as `<task_slug>/<feature_name>`.
- Use `architecture/<feature_name>` for architecturer tasks and `develop/<feature_name>` for developer tasks by default.
- Create `docs/<feature_name>` only when docs need a separate architecturer-held branch.

Use `bin/worktree.py` to validate slugs and create worktrees when possible.

## File Contract

Use one file for composer-to-worker commands:

`.agents/tasks/<task_slug>/ASSIGNMENT.md`

Use one file for worker-to-composer completion:

`.agents/tasks/<task_slug>/HANDOFF.md`

Workers must treat `ASSIGNMENT.md` as read-only. Composer must update `ASSIGNMENT.md` for new attempts and revision requests instead of sending task details through scattered prompts.

## Composer Procedure

1. Inspect repository structure, docs, build scripts, and existing tests.
2. Ask the developer only for product intent or tradeoffs that cannot be discovered.
3. Define objective goal, implementation guidelines, acceptance criteria, and validation commands.
4. Create `.agents/templates/assignment.md` and `.agents/templates/handoff.md` from this plugin's templates if they are absent.
5. Create `<feature_name>` and worker branches/worktrees.
6. For each worker, write `.agents/tasks/<task_slug>/ASSIGNMENT.md` with `bin/assignment.py`.
7. Launch only one worker class per batch: architecturer or developer.
8. Worker prompt must be short: "Read and execute `.agents/tasks/<task_slug>/ASSIGNMENT.md`; write `.agents/tasks/<task_slug>/HANDOFF.md` when complete."
9. After HANDOFF.md appears, review diff strictly, run tests, run the app or deployment command when applicable, and inspect terminal output.
10. If review fails, update the same `ASSIGNMENT.md` with a new `Current Command` and `Revision Log` entry, then return the work to the same worker branch.
11. If review passes, merge `<task_slug>/<feature_name>` into `<feature_name>`.
12. After all worker branches are accepted and merged, write or update root `CHANGELOG.md` with the completed feature, worker task summaries, notable implementation details, and validation evidence.
13. In the same final documentation loop, document the additional features and implementations in `docs/**`; create focused docs when none exist, and update existing docs when they already cover the affected subsystem.

## Worker Rules

- Read `ASSIGNMENT.md` before doing anything else.
- Do not modify `ASSIGNMENT.md`.
- Keep changes scoped to the assigned branch and objective.
- Write `HANDOFF.md` before stopping.
- Include changed files, validation commands and output, known risks, and any incomplete work in `HANDOFF.md`.

## Scripts

- `bin/assignment.py`: create, validate, and revise `ASSIGNMENT.md`.
- `bin/worktree.py`: validate branch slugs and create feature/worker worktrees.
- `bin/guard.py`: Claude Code hook guard for composer/worker permissions.
