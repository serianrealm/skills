# Impact Analysis

Map task text onto the graph:

- directly affected files and symbols
- indirectly affected callers, tests, config, runtime paths
- public interfaces at risk
- entry-point to implementation dependency paths
- likely failure modes
- rollback implications
- migration requirements
- files that require explicit approval before modification

Supported query patterns include:

- path from CLI command to provider launcher
- config field definition, validation, and consumption
- impact of interface changes
- modules that can modify integration branches
- files involved in worktree creation and merge gating
