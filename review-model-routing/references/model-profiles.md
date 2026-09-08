# Model Profiles

## Required profile fields

For each target-execution model, record the exact `model_id`, current availability, supported review levels and task capabilities, source/tool access, supported `reasoning_effort`, relative-cost evidence, verified fallback, execution environment, evidence source, and verification date. Unknown fields remain unknown; do not infer capability from a model name.

## Selection

Filter by availability, required review capability, and input/tool access. Apply explicit user model and budget constraints. Choose the lowest-cost remaining capable profile. When cost is unknown, choose the most narrowly suitable verified capability and say that cost was not verified. Add `reasoning_effort` only when the target dispatch API supports it and the task needs it.

The authoring environment and target execution environment may differ. Never use the former's model list to fill an unverified target inventory. Put only the profiles used by the plan in its model snapshot and recheck them before dispatch.

## Optional ChatGPT Work seed

Use this seed only when the target environment currently advertises these exact IDs and capabilities:

| model_id | Suggested level | reasoning_effort |
| --- | --- | --- |
| `gpt-5.6-luna` | `light` | `low` |
| `gpt-5.6-sol` | `standard` | `medium` |
| `gpt-6-astra` | `deep`, `critical` | `high` |

Source: ChatGPT Work model selector metadata verified 2026-09-08. It describes Luna as fast/economical, Sol as a reliable daily agentic model, and Astra as the most capable model for complex work. This is a routing seed, not a performance benchmark or price claim. Reverify availability and parameter support at use time.

When no valid inventory exists, preserve review level, scope, evidence, and dependency placement; set `model: null` and `status: blocked_model_config`, then list the exact target-environment metadata needed to unblock execution.
