# Interface Contracts

Requirement freeze must separate:

- confirmed requirements
- explicit non-goals
- engineering assumptions
- unresolved product decisions
- compatibility constraints
- performance or reliability requirements
- security and external-tool constraints

Do not generate Action Packets when an unresolved question materially affects correctness. Emit `OPEN_QUESTIONS` with concise questions and impact.
