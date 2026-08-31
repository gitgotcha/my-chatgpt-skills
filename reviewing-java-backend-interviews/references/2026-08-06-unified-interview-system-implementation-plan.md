# Unified Interview System Implementation Plan

> **Archived / superseded; paths below are historical and MUST NOT be used for writes.**
>
> 该计划描述的 `candidate_id`、CandidateIndex、`candidates/<candidate_id>/`、`profile/current_profile.json` 与原始 transcript/报告云端上传均已废弃。当前契约以 [shared-interview-system-design.md](shared-interview-system-design.md)、[profile-contract.md](profile-contract.md) 和 [google-drive-runtime.md](google-drive-runtime.md) 为准：按姓名解析全局 `userId`，事件与快照位于 `DriveRoot/my-chatGPT-skills/users/<userId>/interview/`，所有云端写入只经 `submit_event`。

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a shared, versioned candidate/session/review protocol in the two authorized Skills, with deterministic profile updates and a safe mock-to-review handoff.

**Architecture:** `reviewing-java-backend-interviews` owns the sole Python review/profile core and the filesystem test adapter. `conducting-java-backend-mock-interviews` validates confirmation and session material, plans questions, then seals an immutable handoff artifact. Both Skills carry byte-identical schemas; their documentation describes the same state machine and treats unavailable cloud persistence or cross-Skill execution as explicit pending states.

**Tech Stack:** Python 3.12, standard library `json`/`unittest`, `python-docx`, JSON Schema Draft 2020-12 documents, bundled Poppler/document rendering tools.

## Global Constraints

- Modify only `conducting-java-backend-mock-interviews` and `reviewing-java-backend-interviews`; do not read or write actual candidate data.
- Keep real data in ChatGPT Library at runtime; Python supplies validation, deterministic transforms, reports and local test doubles only.
- No dynamic Skill invocation may be assumed. A mock session becomes `review_pending` unless reviewing is explicitly available to consume its sealed handoff.
- Every candidate read/write requires a locked `ConfirmedCandidateContext.candidate_id`; names are display data, never keys.
- Schemas and shared contract copies must be byte-identical and are versioned by `schema_version: "1.0"`.
- Technical evidence is isolated by domain; general competencies may accumulate across domains. Resume claims are question context only.
- Profile events are idempotent on `candidate_id + session_id + review_version` and use optimistic `profile_version` checks.
- All unit and end-to-end tests use a temporary directory and `TEST-*` fictional candidates.
- The parent directory is not a Git repository. Record verification output; do not require a commit.

---

## Locked file structure

- Create in both Skills: `schemas/README.md`, `schemas/contracts.schema.json`, `schemas/manifest.json`.
- Create in reviewing: `scripts/interview_core.py`, `scripts/storage_protocol.py`, `tests/test_interview_core.py`, `tests/test_storage_protocol.py`, `tests/test_end_to_end.py`, `tests/fixtures.py`.
- Create in conducting: `scripts/mock_handoff.py`, `tests/test_mock_handoff.py`, `tests/test_cross_skill_contract.py`.
- Modify in both Skills: `SKILL.md`, `references/*.md`, `agents/openai.yaml`, and the existing report scripts/tests. Human-facing instructions are verified by a final manual workflow audit; automated tests cover their executable artifacts, not wording.

### Task 1: Versioned shared contract

**Files:**
- Create: `reviewing-java-backend-interviews/schemas/contracts.schema.json`
- Create: `conducting-java-backend-mock-interviews/schemas/contracts.schema.json`
- Create: `reviewing-java-backend-interviews/schemas/manifest.json`
- Create: `conducting-java-backend-mock-interviews/schemas/manifest.json`
- Create: `reviewing-java-backend-interviews/schemas/README.md`
- Create: `conducting-java-backend-mock-interviews/schemas/README.md`
- Test: `reviewing-java-backend-interviews/tests/test_interview_core.py`
- Test: `conducting-java-backend-mock-interviews/tests/test_cross_skill_contract.py`

**Interfaces:**
- Produces `SCHEMA_VERSION = "1.0"` and named definitions for every artifact in the design.
- Produces `validate_artifact(data: dict[str, object], schema_name: str) -> dict[str, object]` in Task 2.

- [ ] **Step 1: Write failing schema-consistency tests**

```python
def test_schema_copies_are_byte_identical() -> None:
    assert reviewing_schema.read_bytes() == conducting_schema.read_bytes()

def test_candidate_context_requires_explicit_confirmation() -> None:
    with self.assertRaises(ArtifactValidationError):
        validate_artifact({"candidate_id": "TEST-001"}, "ConfirmedCandidateContext")
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `& $python -m unittest tests.test_interview_core tests.test_cross_skill_contract -v`

Expected: import/module failure because the schema files and validator do not exist.

- [ ] **Step 3: Add the contract document and manifest**

Define Draft 2020-12 `$defs` for `CandidateSummary`, `Candidate`, `CandidateIndex`, `ResumeIndex`, `ResumeMetadata`, `ResumeClaims`, `ConfirmedCandidateContext`, `QuestionAnswer`, `InterviewSession`, `Review`, `CandidateProfile`, `ProfileUpdateEvent`, `CorrectionEvent`, and `CommitRecoveryState`. Require `schema_version`, stable IDs, ISO timestamps and candidate lock fields. `QuestionAnswer` must require `question_id`, `domain`, `source_tags` and `topic_tags`; it may include `resume_claim_ids` and `retest_weakness_ids`. `InterviewSession.source_type` is exactly `mock_interview` or `real_interview`; it requires an evidence confidence in `[0, 1]`.

- [ ] **Step 4: Re-run focused tests**

Run: `& $python -m unittest tests.test_cross_skill_contract -v`

Expected: PASS for the identical-copy test; validator test remains pending until Task 2.

### Task 2: Deterministic review and profile core

**Files:**
- Create: `reviewing-java-backend-interviews/scripts/interview_core.py`
- Test: `reviewing-java-backend-interviews/tests/test_interview_core.py`

**Interfaces:**
- Consumes: Task 1 schema definitions and an in-memory profile/event mapping.
- Produces:

```python
class ArtifactValidationError(ValueError): ...
class CandidateLockError(ValueError): ...
class ProfileConflictError(ValueError): ...
def validate_artifact(data: dict[str, object], schema_name: str) -> dict[str, object]: ...
def resolve_domain(explicit: str | None, resume_domains: list[str], profile_domains: list[str]) -> str | None: ...
def plan_question_sources(has_resume: bool, total_questions: int) -> dict[str, int]: ...
def apply_review_event(profile: dict[str, object], event: dict[str, object]) -> dict[str, object]: ...
def rebuild_profile(snapshot: dict[str, object], active_events: list[dict[str, object]], correction: dict[str, object] | None) -> dict[str, object]: ...
```

- [ ] **Step 1: Write failing behavior tests**

```python
def test_apply_event_is_idempotent_and_domain_isolated() -> None:
    first = apply_review_event(profile(), llm_event())
    second = apply_review_event(first, llm_event())
    assert second == first
    assert "llm_engineering" in second["domain_profiles"]
    assert "llm-engineering weakness" not in second["domain_profiles"].get("java_backend", {})

def test_rebuild_replaces_v1_and_replays_later_event() -> None:
    rebuilt = rebuild_profile(snapshot_before_v1(), [v1(), v1_replacement(), v2()], correction())
    assert rebuilt["head_event_id"] == "EVT-V2"
    assert rebuilt["domain_profiles"]["java_backend"]["weaknesses"]["W-1"]["status"] == "improving"
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `& $python -m unittest tests.test_interview_core.DeterministicProfileTests -v`

Expected: FAIL because `interview_core` cannot be imported.

- [ ] **Step 3: Implement the minimal deterministic core**

Use `json.loads` and explicit type checks for the project-owned schema subset; never call an LLM. Reject unconfirmed/mismatched candidate IDs, malformed artifacts, duplicate application keys and stale expected versions. Update `domain_profiles[domain].weaknesses` only for technical evidence in that domain, while applying communication/project-expression deltas to `general_competencies`. Move a weakness from `open` to `improving` only with saved retest evidence; close only after two distinct passing session IDs and question variants. `resolve_domain` returns `None` for ambiguous mixed material, otherwise follows explicit > resume > profile > `java_backend`. Source planning returns counts whose retest share is never greater than 40%.

- [ ] **Step 4: Re-run the core tests**

Run: `& $python -m unittest tests.test_interview_core -v`

Expected: PASS for validation, selection, source ratios, idempotency, domain isolation, optimistic conflict and correction replay.

### Task 3: Atomic local test storage and recovery protocol

**Files:**
- Create: `reviewing-java-backend-interviews/scripts/storage_protocol.py`
- Create: `reviewing-java-backend-interviews/tests/test_storage_protocol.py`

**Interfaces:**
- Consumes: Task 2 `validate_artifact`, a `Path` test root and `ConfirmedCandidateContext`.
- Produces:

```python
class LocalTestStore:
    def confirm_candidate(self, candidate_id: str, confirmed_by_user: bool) -> dict[str, object]: ...
    def read_candidate_summary(self, query: str | None = None) -> list[dict[str, object]]: ...
    def seal_session(self, context: dict[str, object], session: dict[str, object], transcript: str) -> Path: ...
    def commit_profile_event(self, context: dict[str, object], event: dict[str, object], expected_version: int) -> dict[str, object]: ...
    def recover(self, context: dict[str, object]) -> dict[str, object]: ...
```

- [ ] **Step 1: Write failing atomicity and isolation tests**

```python
def test_unconfirmed_or_wrong_candidate_cannot_read_or_write(self) -> None:
    with self.assertRaises(CandidateLockError):
        self.store.seal_session(unconfirmed_context(), mock_session("TEST-A"), "Q/A")
    context = self.store.confirm_candidate("TEST-A", True)
    with self.assertRaises(CandidateLockError):
        self.store.seal_session(context, mock_session("TEST-B"), "Q/A")

def test_event_conflict_leaves_current_profile_unchanged(self) -> None:
    before = self.store.current_profile("TEST-A")
    with self.assertRaises(ProfileConflictError):
        self.store.commit_profile_event(context_a(), event_a(), expected_version=99)
    assert self.store.current_profile("TEST-A") == before
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `& $python -m unittest tests.test_storage_protocol -v`

Expected: FAIL because `LocalTestStore` does not exist.

- [ ] **Step 3: Implement only the filesystem test double**

Create the documented logical tree below a supplied temporary root. Persist immutable sessions/reviews/events with `x` creation semantics; write prospective profiles to a temporary sibling then atomically replace the allowed current-profile pointer after deterministic validation. Persist recovery state before each mutating phase. Inject named failpoints `after_session`, `after_review`, `after_report`, `after_profile_switch` so recovery can prove that raw evidence survives and partial profiles are never visible. This class is test-only and must not claim to call a Library API.

- [ ] **Step 4: Re-run storage tests**

Run: `& $python -m unittest tests.test_storage_protocol -v`

Expected: PASS for same-name isolation, lock enforcement, version conflicts, duplicate events and all recovery failpoints.

### Task 4: Mock execution contracts and sealed handoff

**Files:**
- Create: `conducting-java-backend-mock-interviews/scripts/mock_handoff.py`
- Create: `conducting-java-backend-mock-interviews/tests/test_mock_handoff.py`
- Modify: `conducting-java-backend-mock-interviews/references/candidate-profile-integration.md`
- Modify: `conducting-java-backend-mock-interviews/references/interview-protocol.md`
- Modify: `conducting-java-backend-mock-interviews/references/report-rubric.md`

**Interfaces:**
- Consumes: confirmed context, selected `resume_id | None`, current domain, question/answer records and `review_pending` status.
- Produces:

```python
class HandoffValidationError(ValueError): ...
def lock_resume(context: dict[str, object], resume_id: str | None) -> dict[str, object]: ...
def create_mock_session(context: dict[str, object], questions: list[dict[str, object]]) -> dict[str, object]: ...
def seal_review_handoff(context: dict[str, object], session: dict[str, object], transcript: str) -> dict[str, object]: ...
```

- [ ] **Step 1: Write failing handoff tests**

```python
def test_no_resume_or_profile_defaults_to_java_backend() -> None:
    session = create_mock_session(confirmed_context(), [])
    assert session["selected_domain"] == "java_backend"
    assert session["state"] == "review_pending"

def test_resume_claims_plan_questions_without_becoming_evidence() -> None:
    session = create_mock_session(resume_context(), redis_lua_mysql_mq_questions())
    assert {"Redis", "Lua", "MySQL", "MQ"} <= set(session["covered_topics"])
    assert "evidence_delta" not in session["resume_claims"]
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `& $python -m unittest tests.test_mock_handoff -v`

Expected: FAIL because the handoff module does not exist.

- [ ] **Step 3: Implement session sealing and protocol documentation**

Validate the candidate lock before any session material is constructed. Enforce an explicit domain choice when mixed material is ambiguous. Lock the selected resume version and retain only its claim IDs in each question. Generate `MOCK-YYYYMMDD-NNN` IDs, source tags and question metadata. Limit variant retests to 40% and never duplicate an old prompt verbatim. `seal_review_handoff` returns a validated artifact with a transcript checksum and `review_pending`; it does not score, create a report, or modify a profile.

- [ ] **Step 4: Re-run mock tests**

Run: `& $python -m unittest tests.test_mock_handoff -v`

Expected: PASS for identity guard, default domain, ambiguity, resume coverage, source ratio, weak-point variants and pending handoff.

### Task 5: Unified review orchestration and report payloads

**Files:**
- Modify: `reviewing-java-backend-interviews/scripts/create_review_report.py`
- Modify: `conducting-java-backend-mock-interviews/scripts/create_interview_report.py`
- Modify: `reviewing-java-backend-interviews/tests/test_create_review_report.py`
- Modify: `conducting-java-backend-mock-interviews/tests/test_create_interview_report.py`
- Modify: `reviewing-java-backend-interviews/references/review-protocol.md`
- Modify: `reviewing-java-backend-interviews/references/profile-contract.md`

**Interfaces:**
- Consumes: a validated Review containing `source_type`, `evidence_type`, `evidence_confidence`, candidate/session/review metadata and per-question evaluation.
- Produces: `raw_transcript.md`, `review_vN.json`, `profile_update_event_vN.json` and `review_report_vN.docx`, or an explicit pending state.

- [ ] **Step 1: Write failing report payload tests**

```python
def test_review_report_includes_identity_source_and_profile_summary(self) -> None:
    create_review_report(source, output)
    text = document_text(output)
    self.assertIn("TEST-20260806-001", text)
    self.assertIn("真实面试", text)
    self.assertIn("画像变化摘要", text)

def test_mock_report_is_not_emitted_before_review_handoff() -> None:
    with self.assertRaises(ValueError):
        create_report(mock_pending_handoff_path, output)
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `& $python -m unittest tests.test_create_review_report tests.test_create_interview_report -v`

Expected: FAIL because required metadata is neither validated nor rendered.

- [ ] **Step 3: Adapt both report generators without duplicating review logic**

Make reviewing's report render the shared Review fields: ID/name, type, domain, session ID, review version, evidence confidence, original answer, loss attribution, spoken answer, reference answer, follow-up linkage, update summary and guidance. The conducting report must reject `review_pending` handoffs and retain compatibility for completed reviewed mock records only. Keep Chinese fonts, tables and section headings. Do not let either script persist cloud files.

- [ ] **Step 4: Re-run report tests**

Run: `& $python -m unittest tests.test_create_review_report tests.test_create_interview_report -v`

Expected: PASS, including legacy report sections and the new traceability fields.

### Task 6: Skill instructions, metadata and recovery wording

**Files:**
- Modify: `conducting-java-backend-mock-interviews/SKILL.md`
- Modify: `conducting-java-backend-mock-interviews/agents/openai.yaml`
- Modify: `reviewing-java-backend-interviews/SKILL.md`
- Modify: `reviewing-java-backend-interviews/agents/openai.yaml`
- Modify: `conducting-java-backend-mock-interviews/tests/test_profile_mode_contract.py`
- Create: `reviewing-java-backend-interviews/tests/test_artifact_layout.py`

**Interfaces:**
- Consumes: schema locations and the Task 4 sealed handoff semantics.
- Produces: executable human-facing workflows, plus schema/metadata artifacts validated by runnable tests. The workflows are manually audited for identity confirmation and pending-state wording.

- [ ] **Step 1: Write failing artifact and behavior tests**

```python
def test_layout_exposes_complete_versioned_contract() -> None:
    manifest = json.loads((root / "schemas" / "manifest.json").read_text(encoding="utf-8"))
    self.assertEqual(manifest["schema_version"], "1.0")
    self.assertEqual(set(manifest["artifacts"]), REQUIRED_ARTIFACTS)

def test_profile_mode_contract_rejects_unconfirmed_identity() -> None:
    with self.assertRaises(HandoffValidationError):
        create_mock_session({"candidate_id": "TEST-A"}, [])
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `& $python -m unittest tests.test_profile_mode_contract tests.test_artifact_layout -v`

Expected: FAIL because the contract manifest and behavior guard do not exist.

- [ ] **Step 3: Update Skill workflows and metadata**

Remove references to `interview-arena-data`, `profile_store.py`, target IDs and `D:\\Interviews`. State that both Skills first read only CandidateIndex summaries, require explicit second confirmation, then lock context. Document resume selection, real material priority, domain ambiguity, one-question cadence, mock-to-review handoff, real-review confirmation, recovery and cloud limits. Preserve each Skill's distinct responsibility. Manually audit this workflow after tests; do not add brittle text-grep assertions.

- [ ] **Step 4: Re-run documentation tests**

Run: `& $python -m unittest tests.test_profile_mode_contract tests.test_artifact_layout -v`

Expected: PASS.

### Task 7: Local end-to-end verification and DOCX page rendering

**Files:**
- Create: `reviewing-java-backend-interviews/tests/test_end_to_end.py`
- Create: `reviewing-java-backend-interviews/tests/fixtures.py`
- Modify: both report test modules only as needed to expose generated fixture paths.

**Interfaces:**
- Consumes: all prior tasks with only temporary roots and `TEST-*` fixture data.
- Produces: deterministic local evidence for each required lifecycle, plus rendered page images retained only for the test duration.

- [ ] **Step 1: Write failing end-to-end tests**

```python
def test_mock_review_updates_profile_and_next_mock_reads_guidance(self) -> None:
    context, first = complete_mock_review_with_chm_weakness(store)
    second = create_mock_session(context, variant_chm_questions())
    self.assertIn("W-CHM-001", second["retest_weakness_ids"])
    self.assertLessEqual(retest_share(second), 0.40)

def test_real_review_waits_for_confirmation_then_applies_once(self) -> None:
    pending = create_real_review(store, context, real_session())
    self.assertEqual(store.current_profile(context["candidate_id"])["profile_version"], 0)
    confirm_real_review(store, context, pending)
    self.assertEqual(store.current_profile(context["candidate_id"])["profile_version"], 1)
    confirm_real_review(store, context, pending)
    self.assertEqual(store.current_profile(context["candidate_id"])["profile_version"], 1)
```

Include explicit tests for all twenty user scenarios: duplicate names/locks; first Java mock; automatic reviewed mock path; Redis/Lua/MySQL/MQ coverage; non-evidentiary resume claims; ConcurrentHashMap variant; 40% cap; real pending/accept/reject; duplicate event; V1/V2 replay; candidate A/B isolation; default Java; LLM resume mock; algorithm real review; ambiguous mixed material; cross-domain technical isolation; cross-domain general competencies; each failpoint; and Markdown/JSON/DOCX downloadable artifacts.

- [ ] **Step 2: Run end-to-end tests and verify failure**

Run: `& $python -m unittest tests.test_end_to_end -v`

Expected: FAIL until the complete lifecycle is wired through all earlier tasks.

- [ ] **Step 3: Complete only integration glue required by failing tests**

Use `LocalTestStore` to seal every source artifact before review/report/profile work. Generate Markdown/JSON/DOCX in the temporary candidate/session tree, render representative short and long Chinese reports using the documents/PDF render workflow, and assert that at least one nonblank page image is produced per report. Inspect all rendered pages visually before accepting the result.

- [ ] **Step 4: Run all test suites and rendering checks**

Run:

```powershell
& $python -m unittest discover -s 'C:\Users\27846\.codex\skills\conducting-java-backend-mock-interviews\tests' -p 'test_*.py' -v
& $python -m unittest discover -s 'C:\Users\27846\.codex\skills\reviewing-java-backend-interviews\tests' -p 'test_*.py' -v
```

Expected: all tests PASS. Run the DOCX rendering command specified by `documents:documents`, inspect each page image, then record the page counts and any observed layout issue.

### Task 8: Isolated cloud smoke-test decision and completion record

**Files:**
- Create: `reviewing-java-backend-interviews/references/cloud-smoke-test.md`
- Test: `reviewing-java-backend-interviews/tests/test_artifact_layout.py`

**Interfaces:**
- Consumes: confirmed availability of a real ChatGPT Library file tool.
- Produces: an exact, safe smoke-test checklist or an explicit `unverified` outcome.

- [ ] **Step 1: Write the test for an executable no-cloud result**

```python
def test_no_cloud_capability_returns_unverified_without_writes(self) -> None:
    outcome = cloud_smoke_decision(capability=None, candidate_id="TEST-20260806-001")
    self.assertEqual(outcome["status"], "unverified")
    self.assertEqual(outcome["write_requests"], [])
```

- [ ] **Step 2: Run the test and verify failure**

Run: `& $python -m unittest tests.test_artifact_layout.CloudSmokeTests -v`

Expected: FAIL because the cloud decision function does not exist.

- [ ] **Step 3: Add the cloud smoke checklist**

Add `cloud_smoke_decision(capability: object | None, candidate_id: str) -> dict[str, object]` to `storage_protocol.py`, returning `unverified` and no writes without a real capability. Specify an isolated directory, only `TEST-*` candidates, exact created artifact inventory, mock handoff/review/profile progression, real pending/confirmation flow, download checks and limited cleanup of only paths created in that run. State that no available Library tool means no write attempt and an `unverified` result.

- [ ] **Step 4: Run final test suite and repository hygiene check**

Run:

```powershell
& $python -m unittest discover -s 'C:\Users\27846\.codex\skills\conducting-java-backend-mock-interviews\tests' -p 'test_*.py' -v
& $python -m unittest discover -s 'C:\Users\27846\.codex\skills\reviewing-java-backend-interviews\tests' -p 'test_*.py' -v
Get-ChildItem -Recurse -File 'C:\Users\27846\.codex\skills\conducting-java-backend-mock-interviews','C:\Users\27846\.codex\skills\reviewing-java-backend-interviews' | Select-String -Pattern '真实候选人|D:\\Interviews'
```

Expected: all tests PASS; search finds no prohibited runtime dependency or actual candidate material. Mark cloud smoke **unverified** unless a real Library tool actually completed the isolated test.
