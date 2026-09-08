# Review Model Routing Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a discoverable `review-model-routing` Skill that assigns concrete reviewer models and embeds executable review gates while generating or revising software implementation plans.

**Architecture:** Keep the core workflow in `SKILL.md`, move target-environment model resolution and the review-gate schema into two progressive-disclosure references, and store realistic routing cases as behavioral fixtures. Integrate the Skill through the repository's single-workflow root router and document it as the eighth repository Skill.

**Tech Stack:** Markdown Agent Skills, OpenAI `agents/openai.yaml`, Python 3 standard-library `unittest` contract tests.

**Spec:** `docs/superpowers/specs/2026-09-08-review-model-routing-design.md`

## Global Constraints

- Create a plain Skill. Do not add profile events, profile schemas, Drive access, identity resolution, or persistence behavior.
- `review-model-routing/SKILL.md` frontmatter contains only `name` and `description`; `name` equals the folder name and `description` begins with `Use when`.
- Preserve `AGENTS.md`'s “Read exactly one workflow” rule by making plan generation, project learning, and Skill creation triggers disjoint.
- Keep exact model IDs and capabilities sourced from the target execution environment. Unknown data remains unknown.
- New review gates start `pending`; future model selection never implies that a review ran or passed.
- Critical tasks receive both pre-implementation and post-implementation gates.
- Prefer the lowest-cost model that satisfies the verified risk requirements.
- Do not create a per-Skill README, script, schema, or empty directory.

## Reviewer model snapshot for this plan

The following IDs and reasoning controls were available in ChatGPT Work when this plan was written on 2026-09-08. The executor must recheck availability before each review dispatch.

| Review level | Model | Reasoning effort | Use in this plan |
| --- | --- | --- | --- |
| Light | `gpt-5.6-luna` | `low` | Documentation judgment only when deterministic checks are insufficient |
| Standard | `gpt-5.6-sol` | `medium` | Root routing integration |
| Deep / Critical | `gpt-6-astra` | `high` | Core Skill semantics and behavioral coverage |

Exact price data was not supplied, so this table expresses a capability/cost preference rather than a numeric cost claim.

---

### Task 1: Implement the plain Skill package and its behavior contract

**Files:**
- Create: `review-model-routing/SKILL.md`
- Create: `review-model-routing/agents/openai.yaml`
- Create: `review-model-routing/references/model-profiles.md`
- Create: `review-model-routing/references/review-block.md`
- Create: `review-model-routing/tests/behavior-scenarios.md`
- Create: `tests/test_review_model_routing_contract.py`

**Interfaces:**
- Consumes: an approved software design or existing implementation plan, source evidence when available, target-environment model metadata, and user budget/model constraints.
- Produces: risk-classified implementation tasks with task-local review gates, concrete model IDs or `blocked_model_config`, dependency edges, pass conditions, and reviewer prompts.

- [ ] **Step 1: Write the failing repository contract test**

Create `tests/test_review_model_routing_contract.py`:

```python
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "review-model-routing"


class ReviewModelRoutingContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

    def test_plain_skill_shape_and_metadata(self):
        frontmatter = self.skill.split("---", 2)[1]
        keys = set(re.findall(r"(?m)^([a-z_]+):", frontmatter))
        self.assertEqual(keys, {"name", "description"})
        self.assertRegex(frontmatter, r"(?m)^name: review-model-routing$")
        self.assertRegex(frontmatter, r"(?m)^description: Use when")
        self.assertNotIn("profile.", self.skill)
        for forbidden in (
            "schemas/profile-capability.json",
            "references/profile-contract.md",
            "tests/test_profile_contract.py",
        ):
            self.assertFalse((SKILL_ROOT / forbidden).exists(), forbidden)

    def test_progressive_disclosure_resources_exist(self):
        for relative in (
            "references/model-profiles.md",
            "references/review-block.md",
            "tests/behavior-scenarios.md",
        ):
            with self.subTest(relative=relative):
                path = SKILL_ROOT / relative
                self.assertTrue(path.is_file(), relative)
                self.assertTrue(path.read_text(encoding="utf-8").strip(), relative)
        self.assertIn("references/model-profiles.md", self.skill)
        self.assertIn("references/review-block.md", self.skill)

    def test_risk_and_gate_invariants_are_explicit(self):
        for token in (
            "light", "standard", "deep", "critical",
            "pre_implementation", "post_implementation",
            "pending", "blocked_model_config",
        ):
            self.assertIn(token, self.skill)
        review_block = (SKILL_ROOT / "references/review-block.md").read_text(
            encoding="utf-8"
        )
        for field in (
            "model:", "execution_mode:", "inputs:", "checks:",
            "pass_when:", "on_failure:", "on_unavailable:",
        ):
            self.assertIn(field, review_block)

    def test_behavior_scenarios_cover_risk_and_configuration_edges(self):
        scenarios = (SKILL_ROOT / "tests/behavior-scenarios.md").read_text(
            encoding="utf-8"
        )
        for case in (
            "copy-only", "tenant-isolation", "outbox-transaction",
            "missing-model-inventory", "existing-plan-change",
        ):
            self.assertIn(case, scenarios)

    def test_openai_adapter_allows_implicit_discovery(self):
        adapter = (SKILL_ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn('default_prompt: "Use $review-model-routing', adapter)
        self.assertIn("allow_implicit_invocation: true", adapter)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new test and confirm the package is missing**

Run:

```bash
python -m unittest tests.test_review_model_routing_contract -v
```

Expected: ERROR in `setUpClass` because `review-model-routing/SKILL.md` does not exist.

- [ ] **Step 3: Create the core Skill entrypoint**

Create `review-model-routing/SKILL.md` with this complete contract:

```markdown
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
```

- [ ] **Step 4: Create the model-resolution reference**

Create `review-model-routing/references/model-profiles.md`:

```markdown
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
```

- [ ] **Step 5: Create the embedded gate reference**

Create `review-model-routing/references/review-block.md`:

````markdown
# Embedded Review Gate

Instantiate every field; do not leave angle-bracket placeholders in a delivered plan. If a source path, command, or model lacks evidence, name it as a blocking input instead of inventing it.

```yaml
review:
  id: "R-01"
  tasks: ["T-01"]
  phase: "post_implementation"
  after: ["T-01"]
  blocks: ["T-02"]
  level: "standard"
  status: "pending"
  model: "gpt-5.6-sol"
  reasoning_effort: "medium"
  execution_mode: "automatic"
  reason: "Bounded behavior change requiring requirement and source review"
  inputs:
    - "Approved design: docs/superpowers/specs/example-design.md"
    - "Task T-01 diff and exact base commit"
    - "Task T-01 test command and captured result"
  checks:
    - "The observable behavior matches the approved acceptance criteria"
    - "The implementation does not expand the approved scope"
  pass_when:
    - "Every check has sufficient evidence and no blocker remains"
  on_failure: "Return to T-01, repair the affected scope, then rerun R-01"
  on_unavailable: "Pause R-01 unless a verified equally capable fallback exists"
```

Omit `reasoning_effort` when unsupported. Use `automatic` only with a verified dispatch mechanism; otherwise write `manual_handoff`. Pre-implementation inputs contain the design, current source, test design, and risk controls. Post-implementation inputs add the exact diff/version and actual verification output.

Attach an instantiated prompt:

> Review task T-01 at the post-implementation gate. Review only; do not modify code. Read the approved design, the T-01 diff against the named base commit, and the captured test result. Check each listed invariant. First assess the raw evidence independently, then compare the implementer's explanation. Return `pass`, `changes_required`, or `insufficient_evidence`. For every issue provide location, evidence, impact, blocking status, and a proposed verification method. Do not assume missing tests passed. The verdict applies only to the named input version.

For `critical` work, the pre-implementation gate blocks the implementation task. The post-implementation gate follows that task and blocks integration, release, or an explicit final delivery gate. Never create a dependency cycle. A combined review still returns one verdict per task.
````

- [ ] **Step 6: Add the OpenAI adapter and realistic behavior scenarios**

Create `review-model-routing/agents/openai.yaml`:

```yaml
interface:
  display_name: "审核模型路由"
  short_description: "为软件执行计划按风险配置具体审核模型和放行门禁"
  default_prompt: "Use $review-model-routing to generate an implementation plan with concrete reviewer models, evidence, checks, and pass gates embedded in each relevant task."

policy:
  allow_implicit_invocation: true
```

Create `review-model-routing/tests/behavior-scenarios.md`:

```markdown
# Behavior Scenarios

## copy-only

Input: change one settings-page button label with no behavior change.
Expected: `light`; deterministic visual/copy verification is sufficient unless judgment adds value; no mandatory deep-model call.

## bounded-csv-export

Input: add CSV export to one module with known fields and authorization rules.
Expected: `standard`; one post-implementation review by a verified standard-capable model; check field mapping, quoting, encoding, and authorization.

## tenant-isolation

Input: add a missing `tenant_id` predicate in a one-line query patch.
Expected: `critical` despite the small diff; pre-implementation review of isolation and regression design, then post-implementation review of the exact diff and cross-tenant test evidence.

## outbox-transaction

Input: change the transaction boundary between order persistence and outbox insertion.
Expected: `critical`; pre-implementation review checks atomicity, retries, and duplicate-event design; post-implementation review checks source and failure-path evidence.

## missing-model-inventory

Input: the plan will run on an environment whose available model IDs and controls cannot be verified.
Expected: author all other plan details; use `model: null`, `status: blocked_model_config`, and list required metadata. Do not copy the current author's model list.

## existing-plan-change

Input: revise one task in a plan with recorded completed reviews elsewhere.
Expected: reset reviews affected by the changed task or input version to `pending`; preserve unrelated completed reviews only when their scope, version, and evidence remain applicable.
```

- [ ] **Step 7: Run the package contract and plain-Skill validator**

Run:

```bash
python -m unittest tests.test_review_model_routing_contract -v
python profile-aware-skill-creator/scripts/validate_profile_skill.py \
  --mode plain review-model-routing
```

Expected: all five contract tests PASS; validator prints `Validation passed (plain)` and exits 0.

- [ ] **Step 8: Forward-test the routing behavior on the scenario set**

Dispatch a fresh agent with the target model inventory from this plan and the five change types in `behavior-scenarios.md`. Instruct it to use `review-model-routing/SKILL.md`, generate a plan, and perform no implementation or review.

Expected evidence:

- copy-only receives a light/no-model justification;
- bounded CSV export receives one standard post gate;
- tenant isolation and outbox transaction each receive critical pre/post gates;
- the missing-inventory variant produces `blocked_model_config` rather than invented IDs;
- every model gate includes all required schema fields and an instantiated prompt.

If any invariant fails, tighten only the relevant Skill instruction, rerun the contract test and validator, and repeat this forward test once.

- [ ] **Step 9: Commit the complete Skill package**

```bash
git add review-model-routing tests/test_review_model_routing_contract.py
git commit -m "feat: add review model routing skill"
```

#### Embedded review gate R-01

```yaml
review:
  id: "R-01"
  tasks: ["T-01"]
  phase: "post_implementation"
  after: ["T-01"]
  blocks: ["T-02"]
  level: "deep"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "automatic"
  reason: "The Skill controls future risk classification, model selection, and execution gates across projects."
  inputs:
    - "docs/superpowers/specs/2026-09-08-review-model-routing-design.md"
    - "Commit produced by Task 1 and its parent commit"
    - "Task 1 unittest, validator, and forward-test outputs"
  checks:
    - "Risk classification follows failure impact rather than diff size"
    - "Critical work receives valid pre/post dependencies"
    - "Unknown model data fails closed without invented IDs or costs"
    - "The Skill remains plain and preserves plan-authoring scope"
  pass_when:
    - "Every check has evidence and no unresolved blocking defect remains"
  on_failure: "Repair Task 1 only, rerun its tests and forward test, then repeat R-01"
  on_unavailable: "Pause T-02 until gpt-6-astra or a verified equally capable deep-review model is available"
```

Reviewer prompt:

> Review Task T-01 at gate R-01. Review only; do not modify files. Read the approved design, the Task 1 commit against its parent, all Skill package files, contract-test output, plain-validator output, and forward-test result. Check risk classification, pre/post critical gates, model-evidence handling, dependency safety, pending-state semantics, and the absence of profile behavior. Return `pass`, `changes_required`, or `insufficient_evidence`. For every issue give the file/location, evidence, impact, blocking status, and proposed verification. The verdict applies only to the reviewed commit.

---

### Task 2: Integrate the Skill into the single-workflow root router

**Files:**
- Modify: `AGENTS.md:3-12`
- Create: `tests/test_review_model_routing_router.py`

**Interfaces:**
- Consumes: the root router's existing “read exactly one workflow” rule and the canonical path `review-model-routing/SKILL.md`.
- Produces: one disjoint plan-generation route while keeping project learning and explicit Skill creation on their current workflows.

- [ ] **Step 1: Write the failing router test**

Create `tests/test_review_model_routing_router.py`:

```python
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReviewModelRoutingRouterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        cls.active = cls.router.split("## Persistence contract", 1)[0]

    def test_router_keeps_exactly_one_workflow_rule(self):
        self.assertIn("Read exactly one workflow before responding", self.active)

    def test_plan_generation_has_its_own_route(self):
        lines = [line for line in self.active.splitlines() if "生成或修改软件执行计划" in line]
        self.assertEqual(len(lines), 1)
        self.assertIn("review-model-routing/SKILL.md", lines[0])

    def test_neighbor_routes_remain_disjoint(self):
        project_line = next(
            line for line in self.active.splitlines()
            if "software-project-learning/SKILL.md" in line
        )
        creator_line = next(
            line for line in self.active.splitlines()
            if "profile-aware-skill-creator/SKILL.md" in line
        )
        self.assertIn("学习", project_line)
        self.assertNotIn("生成或修改软件执行计划", project_line)
        self.assertIn("仅显式调用", creator_line)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the router test and confirm the route is absent**

Run:

```bash
python -m unittest tests.test_review_model_routing_router -v
```

Expected: `test_plan_generation_has_its_own_route` FAILS because zero matching lines exist.

- [ ] **Step 3: Add the disjoint router entry**

Replace the project-learning line and add the new entry before the explicit Skill-creator entry so the active router reads:

```markdown
- 学习软件项目、源码、需求、架构、开发方案或项目面试：`software-project-learning/SKILL.md`
- 根据已批准的设计或开发方案生成或修改软件执行计划，并在计划中配置审核模型与放行门禁：`review-model-routing/SKILL.md`
- 显式创建或更新可复用 Skill（仅显式调用，不隐式触发）：`profile-aware-skill-creator/SKILL.md`
```

- [ ] **Step 4: Run focused router and package tests**

Run:

```bash
python -m unittest \
  tests.test_review_model_routing_router \
  tests.test_review_model_routing_contract -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit the root router integration**

```bash
git add AGENTS.md tests/test_review_model_routing_router.py
git commit -m "feat: route implementation plans through model review"
```

#### Embedded review gate R-02

```yaml
review:
  id: "R-02"
  tasks: ["T-02"]
  phase: "post_implementation"
  after: ["T-02", "R-01"]
  blocks: ["T-03"]
  level: "standard"
  status: "pending"
  model: "gpt-5.6-sol"
  reasoning_effort: "medium"
  execution_mode: "automatic"
  reason: "A small root-router change can misroute several neighboring workflows and needs a bounded semantic review."
  inputs:
    - "AGENTS.md before and after Task 2"
    - "Task 2 commit and parent commit"
    - "Focused router and package test output"
  checks:
    - "Plan generation maps to review-model-routing exactly once"
    - "Project learning still maps to software-project-learning"
    - "Reusable Skill creation remains explicit-only"
    - "The router still requires exactly one workflow"
  pass_when:
    - "All route checks pass and no ambiguous trigger remains"
  on_failure: "Repair AGENTS.md or its focused contract test, rerun Task 2 verification, then repeat R-02"
  on_unavailable: "Pause T-03 until gpt-5.6-sol or a verified standard-capable fallback is available"
```

Reviewer prompt:

> Review Task T-02 at gate R-02. Review only; do not modify files. Compare the Task 2 commit with its parent and read the focused test output. Verify that implementation-plan generation has exactly one route, project learning remains separate, Skill creation remains explicit-only, and the root still instructs agents to read exactly one workflow. Return `pass`, `changes_required`, or `insufficient_evidence` with location, evidence, impact, blocking status, and proposed verification for each issue.

---

### Task 3: Document the eighth Skill and run the repository regression suite

**Files:**
- Modify: `README.md:19-76`
- Modify: `README.md` after `# 6. Profile-Aware Skill Creator`
- Modify: `README.md:1021-1057`
- Create: `tests/test_review_model_routing_readme.py`

**Interfaces:**
- Consumes: the implemented package and root route.
- Produces: discoverable repository documentation that accurately describes plan-time model routing without changing persistence architecture.

- [ ] **Step 1: Write the failing README contract test**

Create `tests/test_review_model_routing_readme.py`:

```python
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReviewModelRoutingReadmeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")

    def test_overview_lists_eight_skills_and_new_entry(self):
        self.assertIn("目前仓库包含 8 个主要 Skill", self.readme)
        self.assertIn("[review-model-routing](./review-model-routing/)", self.readme)

    def test_dedicated_section_describes_plan_time_behavior(self):
        section = self.readme.split("# 6.1 Review Model Routing", 1)[1].split(
            "# 7. Reliable Drive Sync", 1
        )[0]
        for phrase in ("执行计划", "具体模型", "实施前", "实施后", "放行条件"):
            self.assertIn(phrase, section)
        self.assertIn("./review-model-routing/SKILL.md", section)

    def test_quick_navigation_links_the_skill(self):
        quick = self.readme.split("# 23. 快速导航", 1)[1]
        self.assertIn("Review Model Routing", quick)
        self.assertIn("./review-model-routing/", quick)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the README test and confirm documentation is absent**

Run:

```bash
python -m unittest tests.test_review_model_routing_readme -v
```

Expected: all three tests FAIL because the README still lists seven Skills and has no new section or navigation link.

- [ ] **Step 3: Update the overview and topology**

Make these exact documentation changes:

- change `目前仓库包含 7 个主要 Skill。` to `目前仓库包含 8 个主要 Skill。`;
- add the table row `| [review-model-routing](./review-model-routing/) | 生成或修改软件执行计划时，按风险内嵌具体审核模型与放行门禁 | ❌ |`;
- add a `PLAN["Review Model Routing"]` node under `ROOT` in the Mermaid topology;
- add `- Review Model Routing 在计划生成阶段配置审核模型，不执行开发或伪造审核结果。` to the responsibility boundary list.

- [ ] **Step 4: Add the dedicated section and quick navigation entry**

Insert this section between the existing Profile-Aware Skill Creator section and `# 7. Reliable Drive Sync`:

````markdown
# 6.1 Review Model Routing

目录：

```text
review-model-routing/
```

用于根据已批准的设计或开发方案生成、修改软件执行计划。它按照失败后果、推理跨度和证据充分度评估任务，并把具体审核模型、审核输入、检查项、放行条件和失败处理直接写进相关任务。

关键任务会同时获得实施前方案审核和实施后源码/验证证据审核。小改动不会仅因代码行数少而自动降级；无法核验目标执行环境的模型清单时，相关门禁会明确标记为模型配置受阻，不会编造模型或假装审核已经完成。

详细说明：

[review-model-routing/SKILL.md](./review-model-routing/SKILL.md)
````

Add to `# 23. 快速导航`:

```markdown
### 生成带审核模型的开发执行计划

→ [Review Model Routing](./review-model-routing/)
```

- [ ] **Step 5: Run focused tests, the plain validator, and the full Python suite**

Run:

```bash
python -m unittest \
  tests.test_review_model_routing_readme \
  tests.test_review_model_routing_router \
  tests.test_review_model_routing_contract -v
python profile-aware-skill-creator/scripts/validate_profile_skill.py \
  --mode plain review-model-routing
python -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: focused tests PASS, validator exits 0, and all repository-level Python tests PASS.

- [ ] **Step 6: Confirm the change set contains no persistence or profile behavior**

Run:

```bash
git diff --check
git status --short
rg -n "submit_event|profile\\.|system.user|DriveRoot" \
  review-model-routing AGENTS.md tests/test_review_model_routing_*.py
```

Expected: `git diff --check` exits 0; status lists only the planned Skill, tests, router, README, spec, and plan files; `rg` returns no matches.

- [ ] **Step 7: Commit documentation and planning artifacts**

```bash
git add \
  README.md \
  tests/test_review_model_routing_readme.py \
  docs/superpowers/specs/2026-09-08-review-model-routing-design.md \
  docs/superpowers/plans/2026-09-08-review-model-routing-implementation-plan.md
git commit -m "docs: describe review model routing workflow"
```

#### Verification decision for T-03

Level: `light`. No model review is required because this task changes explanatory documentation only, and its claims are bounded by deterministic link, section, package, validator, repository-test, and forbidden-token checks. A human should read the rendered Markdown once before publishing.

---

## Final delivery gate

Before opening a pull request or updating `main`, verify the branch contains exactly the three planned commits, rerun the commands from Task 3 Step 5, and inspect the rendered README links. Publishing to GitHub uses the authorization already given in this conversation, but execution must still preserve the repository's current branch protection and pull-request policy.

Plan complete. After approval, execute with `superpowers:subagent-driven-development` for a fresh implementer per task and the embedded review gates, or use `superpowers:executing-plans` inline with the same gates.
