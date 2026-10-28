# Profile Skill Authoring Standard

This reference applies after the user explicitly asks to create or update a Skill that remembers facts across sessions. Keep the target directory exactly as named by the user; inventory its current `SKILL.md`, references, scripts, schemas, tests, and unrelated work before editing.

## Route decision

1. Decide whether the Skill needs to read or save cross-session state. Ordinary Skills do not need a snapshot.
2. Select a readable nested route such as `knowledge/java/jvm` or `project/12306`. Store it in the capability as a path-segment array, not as one flat domain string. Keep user-provided spelling and hierarchy; Chinese names are allowed. Before creating a new top-level route or an ambiguous path, show the full path and get confirmation. An explicit request to create that exact path is confirmation. The `domain` field is a Skill taxonomy label only; it is not the storage route.
3. Define the JSON snapshot shape, fields, record conditions, revision behavior, and private-data exclusions. Do not create account IDs or derive folder names from identity.
4. Link the Skill to the shared `references/rds-jbryon-runtime.md` contract and use only the `rds` MCP tool for cross-session reads/writes.
5. Add tests for route selection, missing snapshots, immutable original answers, append/revision behavior, same-field conflicts, and status claims.

## Evidence and privacy

Record only user-observable facts that the Skill is authorized to preserve. Do not convert suggestions, generated answers, or planned work into user facts. Keep original answers and coach-written feedback in separate fields. Exclude credentials, source repositories, resumes and personal media unless the user explicitly requests a specific text record and it is appropriate to store.

## Runtime behavior

Resolve existing readable paths before reading. Read the current snapshot and revision before patching. Use a new request ID for a new logical write; retry an unknown outcome with the same ID and exact content. Do not overwrite or silently resolve a same-field conflict. Report a save only after authoritative `projected` status. If RDS-JBryon is unavailable, continue only work that does not require past state and say that the snapshot was not read or saved.
