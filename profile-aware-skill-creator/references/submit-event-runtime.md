# Submit-Event Runtime Protocol

This reference is the single source of truth for the generic profile runtime
protocol used by generated profile-aware Skills. It documents the interface
baseline of the Reliable Drive Sync MCP (protocol revision 2026-09-01). The
MCP exposes exactly one tool:

```text
submit_event
```

Every profile operation — read or write — goes through `submit_event` with a
JSON envelope. A generated Skill must never use a Google Drive connector, a
storage or folder ID, a Drive URL, or any file path to access profile data. A
Skill also never writes or overwrites a profile snapshot directly; snapshots
are rebuilt by the runtime from immutable evidence events.

## Envelope shape

The outer envelope is protocol schemaVersion `"1.2"`. Inner generic-profile
events are schemaVersion `"1.0"`.

```json
{
  "schemaVersion": "1.2",
  "namespace": "profile",
  "eventType": "profile.evidence.recorded",
  "identity": {
    "userId": "11111111-1111-4111-8111-111111111111",
    "username": "alice"
  },
  "payload": { },
  "requestId": "33333333-3333-4333-8333-333333333333"
}
```

- `namespace` must match the first segment of `eventType` (`system` or
  `profile`).
- `identity`, when present, contains exactly `userId` and `username`.
- `requestId` is a fresh non-empty string, ideally a UUID, for each call.
- The examples below use fixed test UUIDs and the `english-learning` domain.
  Generated Skills generate their own UUIDs at runtime.

## Runtime sequence

A generated profile-aware Skill follows this order during a personalized task:

1. Call `system.capabilities.read` once before any profile operation.
2. If the runtime reports the generic profile capability as disabled or
   unsupported (`unsupported_capability`), skip all profile reads and writes
   and continue the ordinary business task. This is fail-closed for profile
   features only — the business answer itself must still be delivered.
3. Ask for or confirm the user's display name, then call
   `system.user.resolve`.
4. On `identity_not_found`, ask the user whether to register. Only an explicit
   yes permits `system.user-registered`.
5. While registration is only `pending` or `cloud_accepted`, continue the
   business task but do not read or write the profile until a later
   `system.user.resolve` confirms the identity.
6. After a verified resolve, call `profile.snapshot.read` before personalized
   work.
7. After the business work, emit at most one consolidated
   `profile.evidence.recorded` event, and only when the Skill's `recordWhen`
   conditions were satisfied.
8. Report the business outcome separately from the persistence state.

## Operation 1: `system.capabilities.read`

Read-only preflight. No identity, no Outbox, no Drive access.

Request:

```json
{
  "schemaVersion": "1.2",
  "namespace": "system",
  "eventType": "system.capabilities.read",
  "payload": {},
  "requestId": "33333333-3333-4333-8333-333333333333"
}
```

Response (success):

```json
{
  "status": "ok",
  "data": {
    "protocolRevision": "2026-09-01",
    "genericProfile": {
      "enabled": true,
      "eventTypes": [
        "system.user.resolve",
        "profile.evidence.recorded",
        "profile.snapshot.read"
      ]
    },
    "receiptSemantics": {
      "pending": "local_outbox",
      "cloud_accepted": "cloud_outbox_drive_pending"
    }
  }
}
```

## Operation 2: `system.user.resolve`

Read-only exact lookup by NFKC-normalized display name.

Request:

```json
{
  "schemaVersion": "1.2",
  "namespace": "system",
  "eventType": "system.user.resolve",
  "payload": {
    "displayName": "alice"
  },
  "requestId": "44444444-4444-4444-8444-444444444444"
}
```

Responses:

- Unique match: `{ "status": "ok", "identity": { "userId": "11111111-1111-4111-8111-111111111111", "username": "alice" } }`
- No match: `identity_not_found`. No file is created; ask the user whether to register.
- Name conflict: `user_conflict`. Stop; do not guess or merge.

## Operation 3: `system.user-registered`

Explicit registration. Only call it after the user said yes.

Request:

```json
{
  "schemaVersion": "1.2",
  "namespace": "system",
  "eventType": "system.user-registered",
  "payload": {
    "displayName": "alice"
  },
  "requestId": "55555555-5555-4555-8555-555555555555"
}
```

Response: an asynchronous write receipt (`pending` or `cloud_accepted`, see
"Receipts" below). Registration is complete for profile purposes only after a
later `system.user.resolve` returns the verified identity.

## Operation 4: `profile.snapshot.read`

Read-only profile read. It never enters the Outbox and never writes files.

Request:

```json
{
  "schemaVersion": "1.2",
  "namespace": "profile",
  "eventType": "profile.snapshot.read",
  "identity": {
    "userId": "11111111-1111-4111-8111-111111111111",
    "username": "alice"
  },
  "payload": {
    "domain": "english-learning"
  },
  "requestId": "66666666-6666-4666-8666-666666666666"
}
```

Response (success):

```json
{
  "status": "ok",
  "data": {
    "domain": "english-learning",
    "projectionState": "snapshot",
    "profile": {
      "schemaVersion": "1.0",
      "userId": "11111111-1111-4111-8111-111111111111",
      "username": "alice",
      "domain": "english-learning",
      "generatedAt": "2026-09-01T10:05:00.000Z",
      "headEventId": "22222222-2222-4222-8222-222222222222",
      "sourceEventKeys": ["vocab-concurrency-stuck-2026-09-01"],
      "openWeaknesses": [
        {
          "dimensionKey": "vocabulary",
          "subjectKey": "concurrency",
          "latestOutcome": "stuck",
          "latestObservedAt": "2026-09-01T10:00:00.000Z",
          "confidence": "high",
          "positiveEvidenceCount": 0,
          "negativeEvidenceCount": 1,
          "partialEvidenceCount": 0,
          "evidenceRefs": ["vocab-concurrency-stuck-2026-09-01"],
          "sourceRefs": ["conversation:2026-09-01:turn-18"]
        }
      ],
      "improvingSignals": [],
      "stableStrengths": [],
      "observations": []
    }
  }
}
```

`projectionState` is `"snapshot"` when a stored snapshot fully covers the
current valid event set, or `"rebuilt_in_memory"` when the runtime rebuilt the
profile from events without writing anything. Both are read-only results.

## Operation 5: `profile.evidence.recorded`

The only write operation. The inner event carries schemaVersion `"1.0"`:

```json
{
  "schemaVersion": "1.2",
  "namespace": "profile",
  "eventType": "profile.evidence.recorded",
  "identity": {
    "userId": "11111111-1111-4111-8111-111111111111",
    "username": "alice"
  },
  "payload": {
    "domain": "english-learning",
    "event": {
      "schemaVersion": "1.0",
      "eventId": "22222222-2222-4222-8222-222222222222",
      "eventKey": "vocab-concurrency-stuck-2026-09-01",
      "observedAt": "2026-09-01T10:00:00.000Z",
      "sourceSkill": "english-learning",
      "action": "observe",
      "observations": [
        {
          "dimensionKey": "vocabulary",
          "subjectKey": "concurrency",
          "outcome": "stuck",
          "evidence": "用户无法解释该单词。",
          "confidence": "high",
          "sourceRef": "conversation:2026-09-01:turn-18"
        }
      ]
    }
  },
  "requestId": "77777777-7777-4777-8777-777777777777"
}
```

Rules:

- `eventKey` is a stable idempotency key: retrying the same event with the same
  key and content is safe; the same key with different content fails with
  `event_key_conflict`.
- `observedAt` is RFC 3339.
- `outcome` is one of `observed`, `consulted`, `stuck`, `incorrect`, `partial`,
  `completed`, `correct`, `passed`, `failed`. Without mastery evidence only
  `observed` or `consulted` are allowed.
- `confidence` is `high`, `medium`, or `low`.
- The caller does not set `userId`, `username`, `domain`, or `contentHash`
  inside the event; the runtime binds the verified identity and domain before
  persistence.
- The domain must match `^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$` and must not be one
  of the reserved names (`algorithm`, `interview`, `resume-knowledge`,
  `system`, `profile`); otherwise the call fails with `invalid_domain`.

### Correction events: `supersede` and `invalidate`

Corrections replace or void an earlier evidence event without deleting
anything. Rules:

- `action: "supersede"` carries new observations plus `targetEventKey`.
- `action: "invalidate"` carries no observations, only `targetEventKey`.
- `targetEventKey` must be an `eventKey` that appears in the `evidenceRefs` of
  a successful `profile.snapshot.read` for the same user and domain.
- The correction's `observedAt` must be strictly later than the target
  evidence's `observedAt`.
- An unknown target fails with `target_event_not_found`; an already corrected
  or invalidated target fails with `target_event_inactive`.

Example invalidate envelope (target key taken from the snapshot read above):

```json
{
  "schemaVersion": "1.2",
  "namespace": "profile",
  "eventType": "profile.evidence.recorded",
  "identity": {
    "userId": "11111111-1111-4111-8111-111111111111",
    "username": "alice"
  },
  "payload": {
    "domain": "english-learning",
    "event": {
      "schemaVersion": "1.0",
      "eventId": "88888888-8888-4888-8888-888888888888",
      "eventKey": "vocab-concurrency-stuck-2026-09-01-retracted",
      "observedAt": "2026-09-02T09:00:00.000Z",
      "sourceSkill": "english-learning",
      "action": "invalidate",
      "targetEventKey": "vocab-concurrency-stuck-2026-09-01",
      "observations": []
    }
  },
  "requestId": "99999999-9999-4999-8999-999999999999"
}
```

## Receipts and error semantics

Write receipts are asynchronous:

- `pending` — the event is durably stored in the local outbox and will be
  delivered automatically. Tell the user the evidence is safely kept and will
  sync.
- `cloud_accepted` — the cloud outbox accepted the event; Drive synchronization
  continues in the background.

A successful write receipt must not be described as a completed Drive file
write, and the Skill must not claim a Drive `fileId`: the initial response
carries no Drive file identifier. Snapshot generation happens asynchronously;
`profile.snapshot.read` rebuilds the profile in memory when needed.

Errors and required behavior:

| Error | Skill behavior |
| --- | --- |
| `unsupported_capability` | Stop profile reads/writes; continue the business answer |
| `identity_not_found` | Ask the user whether to register; never auto-register |
| `identity_mismatch` / `user_conflict` | Stop reads and writes; do not guess the user |
| `invalid_domain` | Stop; never build paths from the rejected domain |
| `invalid_profile_event` | Report the contract error; nothing enters the outbox |
| `event_key_conflict` | Stop; keep the original event |
| `target_event_not_found` | Do not write the correction event |
| `target_event_inactive` | Do not write the correction event again |

Business answers and persistence state are reported separately. A failed
profile write must not erase an already-completed business answer, and a
successful write must not be presented as instant cloud storage.

## Platform portability

The JSON envelope inside `submit_event` is identical across Codex, ChatGPT,
Claude, and WorkBuddy. Only the surrounding tool-call syntax differs by
platform. The four platform adapters therefore produce byte-equivalent JSON
envelopes after JSON canonicalization; a generated Skill contains no
platform-private envelope variants.

## Fail-closed summary

- Capability unavailable → no profile features, business continues.
- Identity unresolved → no profile reads or writes, ask or continue plain.
- Registration pending → no profile reads or writes until a later resolve.
- Any identity error → stop profile work entirely.
