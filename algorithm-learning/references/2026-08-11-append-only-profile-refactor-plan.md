# Append-Only Algorithm Profile Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade algorithm-learning profile persistence to schema 1.2 so every learning event and profile snapshot is created once, never overwritten, and profiles can always be rebuilt from verified event files.

**Architecture:** Keep user selection isolated in immutable registration records under `user-registry/`. Store each learning event in its own JSON file and treat events as the sole source of truth. Derive snapshots from all verified, de-duplicated events and create a fresh snapshot instead of replacing a current pointer.

**Tech Stack:** Markdown skill instructions, JSON schemas, Python `unittest`, Google Drive connector read/create/readback checks.

## Global Constraints

- Use schemaVersion `1.2` for every new registration, identity migration copy, event, and snapshot.
- Never write, replace, append to, or delete `user-index.json`, `event-log.jsonl`, `profile/current/*`, or `profile/history/*`.
- Every cloud create must use a unique filename and be read back with matching `userId`, `username`, `schemaVersion`, and verified parent directory.
- An event creates one fact record. A failed snapshot after a verified event returns `profile_cache_pending`, not `cloud_persistence_pending`.
- Preserve all existing algorithm-answering behaviour and the conversation-level identity gate.

---

### Task 1: Define the schema 1.2 append-only protocol

**Files:**
- Modify: `SKILL.md`
- Modify: `references/algorithm-profile-contract.md`
- Modify: `references/google-drive-runtime.md`
- Modify: `references/algorithm-daily-protocol.md`
- Modify: `references/daily-scheduler-prompt-template.md`
- Test: `tests/test_skill_contract.py`

**Interfaces:**
- Consumes: A validated `{userId, username}` conversation binding and the `algorithm/` Drive root.
- Produces: One verified `event-<eventId>.json` and, when possible, one verified `snapshot-<observedAt>-<eventId>.json`.

- [ ] **Step 1: Write failing contract tests**

```python
def test_append_only_contract_requires_unique_event_and_snapshot_files(self):
    contract = self._read("algorithm-profile-contract.md")
    for required in ("schemaVersion `1.2`", "event-<eventId>.json", "snapshot-<observedAt>-<eventId>.json"):
        self.assertIn(required, contract)

def test_append_only_contract_forbids_legacy_writes(self):
    runtime = self._read("google-drive-runtime.md")
    self.assertIn("禁止调用任何“更新文件内容”的接口", runtime)
```

- [ ] **Step 2: Run the new tests and verify they fail against schema 1.1**

Run: `python -m unittest tests.test_skill_contract -v`

Expected: failures because the existing contract names `event-log.jsonl`, `profile-snapshot.json`, and `profileVersion`.

- [ ] **Step 3: Replace the persistence instructions with schema 1.2 rules**

```text
algorithm/user-registry/registration-<userId>.json
algorithm/users/<userId>/events/event-<eventId>.json
algorithm/users/<userId>/profile/snapshots/snapshot-<UTC>-<eventId>.json
```

Specify event-key idempotency, event de-duplication by earliest valid creation, full-event snapshot rebuild, and the two distinct pending statuses.

- [ ] **Step 4: Run the contract suite and basic Skill validation**

Run: `python -m unittest tests.test_skill_contract -v && python /root/.codex/skills/oai/skill-creator/scripts/quick_validate.py .`

Expected: all tests pass and `Skill is valid!`.

### Task 2: Add executable local verification for the append-only model

**Files:**
- Create: `tests/test_append_only_profile_model.py`
- Modify: `tests/test_skill_contract.py`

**Interfaces:**
- Consumes: Literal schema 1.2 fixtures with event keys, user locks, and snapshot coverage.
- Produces: Verified behaviour for duplicate events, concurrent distinct events, invalid/incomplete snapshots, and username conflicts.

- [ ] **Step 1: Write the failing behaviour tests**

```python
def test_duplicate_event_key_keeps_only_the_earliest_valid_event(self):
    events = [valid_event("e-late", "2026-08-11T10:27:00Z"), valid_event("e-early", "2026-08-11T10:26:00Z")]
    kept, diagnostics = deduplicate_events(events)
    self.assertEqual(["e-early"], [event["eventId"] for event in kept])
    self.assertEqual(["duplicate_event_key"], diagnostics)

def test_incomplete_snapshot_is_rebuilt_from_all_verified_events(self):
    rebuilt = select_or_rebuild_snapshot(events=[event_a, event_b], snapshots=[snapshot_only_for_a])
    self.assertEqual({event_a["eventKey"], event_b["eventKey"]}, set(rebuilt["sourceEventKeys"]))
```

- [ ] **Step 2: Run the model tests and verify missing helpers fail**

Run: `python -m unittest tests.test_append_only_profile_model -v`

Expected: import failure or missing-helper failures before the test implementation is added.

- [ ] **Step 3: Add minimal test-only model helpers**

```python
def deduplicate_events(events):
    valid = sorted(events, key=lambda event: event["createdAt"])
    # validate identity/schema before keeping the first event for each eventKey

def select_or_rebuild_snapshot(events, snapshots):
    # use only a valid snapshot covering every verified event key; otherwise rebuild
```

Keep fixtures and helpers inside the test module because the production artifact is an instruction skill, not a runtime library.

- [ ] **Step 4: Run the complete local suite**

Run: `python -m unittest discover -s tests -v`

Expected: all identity-gate, legacy-answering, append-only, idempotency, recovery, and conflict tests pass.

### Task 3: Migrate the specified Google Drive user without legacy mutation

**Files:**
- Create in Drive: `algorithm/user-registry/registration-1aaa296b-9b35-4546-8dbd-8d97d81a9e8d.json`
- Create in Drive: `algorithm/users/1aaa296b-9b35-4546-8dbd-8d97d81a9e8d/events/event-a02794b5-fce1-4f58-bd8f-3efb978ae7e4.json`
- Create in Drive: one schema 1.2 snapshot under `profile/snapshots/`

**Interfaces:**
- Consumes: Existing verified `identity.json` for user `1aaa296b-9b35-4546-8dbd-8d97d81a9e8d` / `乔炳源` and the existing `algorithm` root.
- Produces: A user-registry record, one immutable “三数之和” event, and one snapshot whose `sourceEventKeys` includes that event.

- [ ] **Step 1: Read and validate the existing identity and parent folders**

Check literal identity values, schema compatibility, and the target parent folder IDs before creating any file.

- [ ] **Step 2: Create and read back the new folders and JSON files**

Create the `user-registry` and `profile/snapshots` folders only when absent. Upload each JSON file once, then read the returned file and list its parent folder to verify the file name and parent.

- [ ] **Step 3: Run cloud acceptance checks**

Verify all of the following against Drive:

```text
registration has schemaVersion 1.2 and matches identity
event contains “三数之和”, “双指针”, consulted, and the fixed eventId
snapshot sourceEventKeys contains the eventKey and headEventId matches the event
old user-index.json and legacy event/profile files still exist unchanged
```

- [ ] **Step 4: Report the exact local and cloud test results**

Report command output counts, created Drive artifacts, readback result, and any unexercised connector failure branch. Do not claim that a snapshot is an authoritative profile record.
