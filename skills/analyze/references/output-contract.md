# Output Contract

Analyzer output must be machine-readable JSON or YAML-compatible data with this shape:

```yaml
analysis_result:
  status: ready | blocked | stale | failed

repository_snapshot:
  repository_root: "<path>"
  branch: "<branch>"
  commit: "<sha>"
  dirty: false
  generated_at: "<timestamp>"

repository_facts:
  languages: []
  package_managers: []
  build_commands: []
  test_commands: []
  lint_commands: []
  typecheck_commands: []
  entry_points: []
  config_files: []
  environment_variables: []

project_graph:
  artifact_path: ".analyzer/graph.json"
  graph_version: 1
  source_commit: "<sha>"
  stale: false
  nodes: []
  edges: []

architecture:
  layers: []
  modules: []
  public_interfaces: []
  protected_boundaries: []
  extension_points: []
  risky_areas: []

requirement_interpretation:
  confirmed_requirements: []
  non_goals: []
  assumptions: []
  open_questions: []

impact_analysis:
  directly_affected: []
  indirectly_affected: []
  dependency_paths: []
  compatibility_risks: []
  likely_failure_modes: []

action_plan:
  packets: []
  dependency_dag: []
  concurrency_groups: []

test_plan:
  existing_coverage: []
  missing_tests: []
  upper_bound_checks: []

evidence:
  claims: []
  low_confidence_items: []

recommended_next_step: ask_user | spawn_actions | stop
```

Evidence claims use:

```yaml
claim:
  text: "<claim>"
  type: static_fact | semantic_interpretation | engineering_inference
  confidence: high | medium | low
  evidence:
    - "<file>:<line or symbol>"
  caveat: "<optional limitation>"
```
