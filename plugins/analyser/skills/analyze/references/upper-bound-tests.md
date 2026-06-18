# Upper-Bound Tests

Upper-bound checks go beyond standard unit tests. Consider:

- dirty worktree
- missing integration branch
- branch naming collision
- malformed Action Packet
- action branch without a commit
- forbidden file modifications
- merge conflict
- interrupted run and resume behavior
- provider timeout or 429/500
- unsupported gateway fields
- invalid configuration
- concurrent resource contention
- maximum expected input size
- user-visible CLI output and exit-code behavior

Passing tests are never the only acceptance condition.
