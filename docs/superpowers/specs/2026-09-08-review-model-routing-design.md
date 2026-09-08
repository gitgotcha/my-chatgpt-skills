# Review Model Routing Skill Design

## Goal

Create a reusable `review-model-routing` Skill that is selected when an agent generates or revises a software implementation plan. The Skill assigns a concrete reviewer model to each necessary review gate and embeds the gate, evidence, checks, pass criteria, and fallback behavior into the relevant plan task.

## Scope

The Skill handles software implementation plans created from an approved design or development proposal. It does not execute development, invoke future reviews while authoring the plan, route production inference traffic, conduct a standalone code review, or persist a user profile.

The repository root router selects this workflow for plan generation and revision. Project learning remains routed to `software-project-learning`; reusable Skill creation remains explicitly routed to `profile-aware-skill-creator`.

## Inputs and output

Inputs may include the approved design, an existing plan, source code, verification evidence, the target execution environment's available model list, and user budget or model preferences.

The output is a complete implementation plan. Every task receives either an embedded model review gate or a written reason why deterministic or human verification is sufficient. A global model snapshot may summarize the models used, but it never replaces task-local review instructions.

## Risk classification

Classify work by failure impact, reasoning span, and evidence quality. Changed line count does not determine risk.

| Level | Typical work | Default gate |
| --- | --- | --- |
| Light | Copy, style, behavior-preserving edits | Use `gpt-5.6-luna` with low reasoning by default; deterministic or human verification may replace it only when no reviewer judgment is needed |
| Standard | One bounded module or local business rule | One post-implementation review |
| Deep | Cross-module behavior, state machines, compatibility work | Deep post-implementation review; split concerns only when the evidence differs |
| Critical | Authorization, tenant isolation, migration, concurrency, irreversible effects | Pre-implementation design gate and post-implementation evidence gate |

High-risk one-line patches remain critical. Reviews may be combined only when they share evidence and dependency placement; a combined review still returns a verdict for each task.

## Model resolution

Read the target environment's current model inventory. Each profile records the exact model ID, availability, supported reasoning controls, source/tool access, suitability, relative cost evidence, fallback, source, and verification date.

Filter out unavailable or incapable models, honor explicit user constraints, then choose the lowest-cost remaining candidate. For a verified ChatGPT Work inventory, the default mapping is light → `gpt-5.6-luna` (low), standard → `gpt-5.6-sol` (medium), and deep/critical → `gpt-6-astra` (high). Unknown price or capability remains unknown. The Skill never invents prices, model IDs, or support for `reasoning_effort`.

If the target model inventory is unavailable, author the rest of the plan and mark affected gates `blocked_model_config` with `model: null`. Such a plan is not ready for unattended execution.

## Embedded gate contract

Each review gate contains:

- unique review ID and related task IDs;
- `pre_implementation` or `post_implementation` phase;
- dependency and blocking relationships;
- risk level and initial status;
- exact model ID, supported reasoning setting, execution mode, and selection reason;
- exact design, code, version, and verification inputs appropriate to the phase;
- concrete invariants and checks;
- pass conditions, repair/review behavior, and unavailable-model behavior;
- an instantiated reviewer prompt that says to review without changing code.

New gates start as `pending`. A changed task resets only the affected existing gates. A selected model does not mean the review has run.

## Review outcomes

The reviewer returns `pass`, `changes_required`, or `insufficient_evidence`. Every issue includes location, evidence, impact, blocking status, and a proposed verification method.

Missing evidence is collected before escalating model strength. Repairs trigger a review of the affected scope. The same unresolved blocker after two repair rounds escalates to a capable stronger model or a human decision. Conflicting model conclusions are resolved from the design, source, and reproducible evidence.

## Repository shape

```text
review-model-routing/
|-- SKILL.md
|-- agents/
|   `-- openai.yaml
|-- references/
|   |-- model-profiles.md
|   `-- review-block.md
`-- tests/
    `-- behavior-scenarios.md

tests/
`-- test_review_model_routing_contract.py
```

`AGENTS.md` gains one disjoint router entry. `README.md` adds the eighth Skill to the overview, topology, responsibility list, a `6.1` section, and quick navigation without renumbering the existing persistence sections.

## Acceptance criteria

- Plan-generation requests discover this Skill without an explicit mention.
- Project-learning and Skill-creation requests keep their existing routes.
- A copy edit receives a light Luna review by default; a model-free waiver is allowed only when acceptance is fully deterministic and reviewer judgment adds no value. A one-line tenant-isolation fix remains critical.
- Critical work receives both pre- and post-implementation gates.
- Missing model configuration produces an explicit blocked gate.
- Every gate has concrete inputs, checks, pass criteria, failure handling, and a future `pending` status.
- The new package is a plain Skill and introduces no profile artifacts or storage behavior.
- All repository contract tests pass.
