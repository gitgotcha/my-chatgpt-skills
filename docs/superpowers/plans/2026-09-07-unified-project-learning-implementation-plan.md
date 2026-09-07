# Unified Software Project Learning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the duplicated project-learning split with one `software-project-learning` package whose interview training is an optional mode and whose standard-mode answers receive evidence-based assessment.

**Architecture:** Rename the current package, keep shared evidence and teaching rules in `SKILL.md`, and move substantial mode-specific behavior into two references. Preserve interview depth while making source and requirements equally valid entry evidence.

**Tech Stack:** Markdown skills, YAML UI metadata, Python `unittest` package contracts.

**Spec:** `docs/superpowers/specs/2026-09-07-unified-project-learning-design.md`

## Global Constraints

- Keep one canonical project-learning Skill package.
- Every new module starts with Mermaid or a relationship table.
- Source or requirements/design documentation is sufficient; simulated code must be labeled.
- Optimization is available in both modes and is not a routing criterion.
- Standard-mode answer assessment is evidence-based and does not create persistent mastery claims.

---

### Task 1: Rename and route the unified package

**Files:**
- Move: `backend-project-learning/` → `software-project-learning/`
- Modify: `AGENTS.md`
- Modify: `README.md`
- Test: `tests/test_software_project_learning_contract.py`

- [x] **Step 1: Write and run the failing package test**
- [x] **Step 2: Rename the package and update active routes**
- [x] **Step 3: Run the package test and confirm the canonical name**

### Task 2: Implement the two teaching modes

**Files:**
- Modify: `software-project-learning/SKILL.md`
- Create: `software-project-learning/references/standard-mode.md`
- Modify: `software-project-learning/references/interview-mode.md`
- Modify: `software-project-learning/references/copy-paste-prompt.md`
- Modify: `software-project-learning/agents/openai.yaml`

- [x] **Step 1: Write the shared evidence and mode-selection contract**
- [x] **Step 2: Add the 10-point standard answer assessment rubric**
- [x] **Step 3: Preserve progressive interview questions and optional STAR training**

### Task 3: Update human documentation and behavior scenarios

**Files:**
- Modify: `software-project-learning/README.md`
- Modify: `software-project-learning/tests/behavior-scenarios.md`
- Modify: `software-project-learning/tests/test_package_contract.py`

- [x] **Step 1: Document source-only, document-only and combined evidence flows**
- [x] **Step 2: Add standard assessment, mode ambiguity and mid-session switching scenarios**
- [x] **Step 3: Update package paths and link checks**

### Task 4: Verify and publish the branch

**Files:**
- Verify: repository diff and all Python contract suites

- [x] **Step 1: Run the renamed package tests**
- [x] **Step 2: Run repository compatibility tests**
- [x] **Step 3: Run the Skill validator and inspect the final diff**
- [ ] **Step 4: Commit, push and update PR #15**
