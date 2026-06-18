---
description: Analyze a repository task into evidence-backed Action Packets.
argument-hint: "<natural-language task>"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

Use the `analyzer` skill from the `analyser` plugin for:

`$ARGUMENTS`

Run deterministic repository survey and static graph construction before semantic interpretation. Produce `.analyzer/reports/<timestamp>-analysis.json` only when explicitly writing analyser-owned artifacts. Do not edit application feature code, create branches, merge branches, or act as a critic.
