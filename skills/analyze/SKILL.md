---
name: analyze
description: "Repository intelligence and task-specification layer, not generic code summarization. Use when a natural-language task must be converted into deterministic repository facts, static project graph data, evidence-backed impact analysis, bounded Action Packets for action agents, and upper-bound checks for strict critic agents."
---

# AAC Analyzer

This skill is a repository intelligence and task-specification layer that prepares reliable, evidence-backed implementation work for downstream action agents and strict critic agents. It is not generic code summarization.

## Operating Rules

- Prefer deterministic repository analysis before LLM interpretation.
- Output persistent artifacts in docs/ 
- Extract structure first: files, modules, imports, symbols, calls, tests, configuration, CLI entry points, environment variables, dependencies, and Git state.
- Add semantic interpretation only where it materially improves task specification.
- Tie every architectural or behavioral conclusion to concrete evidence.
- Do not repeatedly reread the whole repository when a valid graph cache exists.
- Do not edit application feature code, create feature branches, merge branches, or act as a critic.
- Do not scan secret files such as `.env`, private keys, credentials, or token stores. Record environment variable names only, never values.

No installed AAC workflow skills or agents were found during creation. Reuse Action Packet and Critic Review terms as compatibility conventions; do not create a second packet schema.

## Workflow

Run stages in order.

### Stage A - Repository facts and environment survey

Use `scripts/collect_repository_facts.py` and follow `references/repository-survey.md`. Distinguish deterministic facts from inferred interpretation.

### Stage B - Static project graph

Use `scripts/build_static_graph.py` and `scripts/validate_graph.py`. Follow `references/static-analysis.md` and `references/graph-schema.md`.

### Stage C - Semantic enrichment

Read `references/semantic-enrichment.md`, `references/architecture-layering.md`, and `references/evidence-and-confidence.md`. Enrich only high-value nodes with confidence, evidence, and caveats.

### Stage D - Requirement freeze

Read `references/interface-contracts.md` and `references/output-contract.md`. Separate confirmed requirements, non-goals, assumptions, unresolved product decisions, compatibility constraints, reliability constraints, and external-tool constraints. If a critical decision is ambiguous, return `status: blocked` with `open_questions` and do not emit Action Packets.

### Stage E - Impact analysis

Use `scripts/compute_diff_impact.py` when a graph exists. Follow `references/impact-analysis.md`. Identify affected files, symbols, dependency paths, compatibility risks, likely failure modes, rollback concerns, and files that must not be modified without explicit approval.

### Stage F - Task decomposition

Follow `references/task-decomposition.md`. Produce the smallest reasonable set of non-overlapping Action Packets. Each packet must contain task ID, branch name, objective, non-goals, architecture context, public interfaces, allowed files, forbidden files, implementation instructions, fixed input-output tests, acceptance criteria, upper-bound tests, risks, rollback plan, observability requirements, and dependencies.

### Stage G - Test-gap and upper-bound planning

Follow `references/test-gap-analysis.md` and `references/upper-bound-tests.md`. Passing automated tests are never the only acceptance condition.

### Stage H - Human-readable architecture views

After graph validation, generate a human-readable interactive architecture view.

Run:

```text
scripts/render_graph_views.py --repo <path>
```

The renderer may build temporary graph data internally, but must not retain raw graph JSON after completion.

Required output:

```text
.docs/reports/
├── index.html
├── architecture.html
├── architecture.svg
├── package-tree.md
└── architecture-summary.md
```

`architecture.html` is the primary output and must support zoom, pan, search, node selection, dependency inspection, and toggling internal imports/calls.

Render modules by default. Collapse functions and classes into their owning module; collapse dense modules into packages. Use readable repository-relative paths and hide external dependencies unless requested.

Do not treat raw graph data as a deliverable. Analysis is incomplete until `architecture.html` has been generated and linked.

## Persistent Artifacts

Store only human-readable outputs under `docs/reports/`:

```text
docs/
└── reports/
    ├── index.html
    ├── architecture.html
    ├── architecture.svg
    ├── package-tree.md
    ├── architecture-summary.md
    ├── scoped/
    └── impact/
```

* `index.html`: all generated reports and diagrams.
* `architecture.html`: interactive architecture graph.
* `architecture.svg`: static export for documentation.
* `package-tree.md`: package and module structure.
* `architecture-summary.md`: evidence-backed architecture explanation.
* `scoped/`: optional focused interactive diagrams.
* `impact/`: task-specific impact reports and diagrams.

Static graph data, semantic caches, snapshots, and diff overlays are temporary implementation details. Store them only in a temporary directory during execution and delete them before completion.

Do not persist or expose `graph.json`, graph IDs, raw static-analysis records, caches, or intermediate JSON artifacts.
## Script Entry Points

- `scripts/collect_repository_facts.py --repo <path>`
- `scripts/build_static_graph.py --repo <path> [--write]`
- `scripts/compute_diff_impact.py --repo <path> --task "<task>"`
- `scripts/validate_graph.py <graph.json>`
- `scripts/validate_analysis_result.py --input <path-or->`

All scripts are local-only, dependency-light, conservative, and read-only with respect to application source code.
