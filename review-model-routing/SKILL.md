---
name: review-model-routing
description: Use when generating or revising a software implementation plan from an approved design or development proposal, including requests for execution plans, development plans, task breakdowns, or reviewer-model routing. Excludes project-learning sessions, application inference routing, and standalone code reviews that do not change a plan.
---

# Review Model Routing

Assign concrete reviewer models while authoring the implementation plan and embed each executable review gate in its related task. Invoke this workflow automatically for plan generation or revision; preserve the user's model, budget, template, and scope choices.

## Workflow

1. Read the approved design, existing plan, relevant source, and validation evidence. Preserve task IDs, dependencies, and user formatting. Run this workflow after task decomposition and before the plan's final self-review. Only author or revise the plan; do not implement work or claim future reviews ran.
2. Classify every deliverable by failure impact, reasoning span, and evidence quality. Changed line count never lowers real risk. Missing evidence becomes a concrete prerequisite instead of an assumption.
3. Read [references/model-profiles.md](references/model-profiles.md). Verify the target execution environment's inventory and select the lowest-cost capable model after honoring explicit user constraints. Use exact model IDs and supported reasoning controls.
4. Read [references/review-block.md](references/review-block.md). Embed a complete gate in the related task. Critical work receives both `pre_implementation` and `post_implementation` gates. Every new gate starts `pending`.
5. Check the completed plan: every task has a review level or a reason deterministic/human verification is sufficient; critical gates bracket implementation; models resolve or use `blocked_model_config`; inputs, checks, pass criteria, failure handling, and unavailable-model handling are concrete; dependencies are acyclic.

## Levels

| Level | Evidence | Default review |
| --- | --- | --- |
| `light` | Copy, style, behavior-preserving, easy rollback | Deterministic or human verification; light model only when judgment adds value |
| `standard` | Bounded module or local business rule | One post-implementation review |
| `deep` | Cross-module flow, state machine, compatibility | Deep post-implementation review; split only when evidence differs |
| `critical` | Authorization, tenant isolation, migration, concurrency, irreversible effects | Pre-implementation design gate and post-implementation evidence gate |

High-risk small patches remain `critical`. Combine reviews only when they share evidence and dependency placement; return a verdict for every related task.

## Outcomes and boundaries

- A selected model is a future assignment. Use `automatic` only when the target executor has a verified dispatch mechanism; otherwise use `manual_handoff`.
- If no verified target inventory exists, finish the remaining plan and set affected gates to `status: blocked_model_config` and `model: null`. Do not substitute the current chat model.
- Reviewers return `pass`, `changes_required`, or `insufficient_evidence` and identify location, evidence, impact, blocking status, and proposed verification for every issue.
- Collect missing evidence before escalating model strength. Re-review affected scope after repair. Escalate the same unresolved blocker after two repair rounds to a capable stronger model or a human decision.
- Resolve conflicting conclusions from the design, source, and reproducible evidence. Do not use majority vote.
- Replace an unavailable model only with a verified equally capable fallback; otherwise stop that gate. Never silently violate user model or budget constraints.
- A reviewer reviews and does not modify code. Model assignment does not authorize future external actions or model calls.
- When revising an existing plan, reset affected gates to `pending`; retain an old completed gate only when its input version and scope remain applicable and evidence is recorded.
