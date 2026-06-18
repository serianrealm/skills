# Task Decomposition

Reuse AAC Action Packet and Critic Review conventions where present. No installed AAC contract files were found when this skill was created, so this skill uses the names as compatibility terms. Do not create a second packet schema or a conflicting critic schema.

Each Action Packet must include:

- `task_id`
- `branch_name`
- `objective`
- `non_goals`
- `architecture_context`
- `public_interfaces_and_invariants`
- `allowed_files`
- `forbidden_files`
- `implementation_instructions`
- `required_fixed_input_output_tests`
- `acceptance_criteria`
- `upper_bound_tests_for_critic`
- `risks_and_mitigations`
- `rollback_plan`
- `observability_requirements`
- `dependencies`

Decomposition rules:

- Minimize overlap between action agents.
- Avoid concurrent tasks that modify the same file or unstable public interface.
- Split by module ownership and dependency boundaries.
- Prefer additive, independently testable changes.
- Mark tasks as serial when interface-first work must land before dependent work.
- Never assign work that requires guessing about unresolved requirements.

Critic Review compatibility:

- Critics verify acceptance criteria and upper-bound behavior.
- Critics do not rely only on passing unit tests.
- Analyzer packets must include enough evidence and forbidden-file boundaries for strict review.
