# Profile Authoring Standard

This reference defines how to author the profile layer of a target Skill. Read
it only after the user has explicitly chosen the profile branch. The runtime
protocol itself lives in [submit-event-runtime.md](submit-event-runtime.md);
the platform-neutral base Skill shape lives in
[portable-skill-standard.md](portable-skill-standard.md).

## Authoring decision record

Before generating any file, record these decisions in order. Each step depends
on the previous one, so do not skip ahead.

1. **Resolved target directory.** Use exactly the path the user named. Record
   whether it already exists. If it exists, inventory `SKILL.md`, `agents/`,
   `references/`, `scripts/`, `schemas/` and tests before touching anything
   (see "Preserving existing directories" below). If the path is missing or its
   meaning is unclear, stop and ask for an explicit path; never substitute a
   default skills directory, `$HOME`, the current repository, or a temporary
   folder.
2. **Plain/profile choice.** Confirm the answer to the single routing question
   ("does this Skill need to save and read a person profile across sessions?").
   The user's current request must have answered it explicitly or by clear
   implication; otherwise ask once before proceeding.
3. **Domain.** Choose one kebab-case domain identifier matching
   `^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$` (2–64 characters). Check it against the
   reserved names that belong to the existing dedicated implementations and the
   protocol itself: `algorithm`, `interview`, `resume-knowledge`, `system`,
   `profile`. A reserved or malformed domain must be rejected, never "fixed"
   silently. The domain is the only storage routing input a Skill owns; the
   runtime derives all storage paths from the verified user and this domain.
4. **`sourceSkill`.** Must equal the generated Skill's folder name (for example
   `english-learning`). It is recorded inside every evidence event as
   `sourceSkill` and must match `profile-capability.json`.
5. **Dimensions.** Define one or more dimensions with a `dimensionKey`, a
   `subjectKeyDescription` (what a stable subject key is for this dimension),
   and a human `description`. Dimension keys follow the same safe-identifier
   rule as the domain.
6. **Observable evidence rules.** Write `recordWhen` conditions that describe
   user-observable behavior only ("the user gave a checkable answer, attempted,
   or explicitly said they were stuck") and `doNotRecordWhen` conditions that
   forbid model-only speculation. Restrict outcomes to the nine protocol
   values (`observed`, `consulted`, `stuck`, `incorrect`, `partial`,
   `completed`, `correct`, `passed`, `failed`); without mastery evidence only
   `observed` or `consulted` are allowed. Evidence text must describe the
   observable behavior, not the model's conclusion.
7. **Minimal added files.** The profile branch adds exactly three artifacts on
   top of the ordinary Skill, plus a minimal link from `SKILL.md`:
   `references/profile-contract.md`, `schemas/profile-capability.json`, and
   `tests/test_profile_contract.py`. A plain-branch Skill must not contain any
   of these three paths, and the profile branch must not add README files,
   changelogs, placeholder assets, or extra scripts without a concrete task.
8. **Validation mode.** Decide the validator mode for the result (`--mode
   profile`) and keep the forward-test evidence: run the validator and the
   generated contract tests before declaring the work finished.

## `profile-capability.json` is not `system.capabilities.read`

`schemas/profile-capability.json` configures a Skill's domain and evidence
vocabulary: its dimensions, its record-when rules, and the runtime operation
names it depends on. `system.capabilities.read` is a live protocol call that
reports whether the deployed runtime currently supports the generic profile
protocol. One is a static authoring artifact; the other is a runtime probe.
They cannot substitute for each other, and a valid capability file never
implies that the runtime is enabled.

## Safe domain and evidence collection

- Validate the domain with the pattern above and the reserved-name list before
  generating any file that embeds it.
- Never construct storage paths, file names, folder IDs, or URLs from the
  domain. The runtime owns path construction; the Skill only submits the
  domain string.
- Collect evidence conservatively: a single negative outcome opens a weakness
  observation; only two positive outcomes from distinct `sourceRef` values
  after the most recent negative can form a strength. When in doubt, record
  `observed` and let the runtime's projection decide.
- The Skill never writes a profile snapshot and never overwrites profile
  state; it only appends immutable evidence events.

## Preserving existing directories

When the resolved target directory already exists, treat its contents as
authoritative user state:

- Read every existing file before writing.
- Preserve unrelated files, fields, custom YAML keys, and user modifications
  byte-for-byte.
- Add the profile artifacts additively; patch `SKILL.md` with the smallest
  link-bearing change rather than rewriting it.
- Never re-run a base initializer over an existing Skill.

## Contract test requirements

The generated `tests/test_profile_contract.py` is a forward test, not a
formality. It must execute and must cover all four runtime behaviors of the
profile contract; a placeholder (for example a single `self.assertTrue(True)`)
is rejected by the validator. Each behavior must appear in the test source by
an unambiguous token, and at least four tests must run and pass:

1. **Capability preflight and fail-closed** — call `system.capabilities.read`
   before any profile operation; when the capability is unsupported, continue
   the business task without profile features.
2. **User consent before profile mutation** — resolve the user with
   `system.user.resolve`, and only call `system.user-registered` after explicit
   consent; never auto-register.
3. **Immutable, read-only evidence** — emit only `profile.evidence.recorded`
   events; `profile.snapshot.read` is read-only and the Skill never writes or
   overwrites a snapshot; no direct Drive or file-path access.
4. **Full scan and preservation of existing files** — when updating an existing
   Skill, read every existing file before writing, preserve unrelated files
   byte-for-byte, and never re-run a base initializer.

## Validation

After generation, run the meta Skill's validator in profile mode and run the
generated `tests/test_profile_contract.py`. Both must pass before the task is
reported complete. Validation failures must be fixed in the generated files,
not silenced by weakening the checks.
