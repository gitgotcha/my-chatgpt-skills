---
name: profile-aware-skill-creator
description: Use when a user explicitly asks to create or update a reusable Skill and wants to decide whether it should read and update a persistent cross-session user profile.
---

# Profile-Aware Skill Creator

Create or update a Skill at the path the user named — that path is
authoritative; never redirect to a default skills directory.
**The named directory is the Skill root**: write `SKILL.md` and all
files directly into it, never into a nested subdirectory. If no path was given,
ask for one and stop. When the target exists, inspect its contents and
preserve every unrelated file, field, and user edit; update in place minimally.

## Ask the single routing question

If the request does not already answer it, ask exactly one question: does this
Skill need to save and read a person profile across sessions? Honor the
answer — never re-ask or decide for the user. That is the only routing
question. When the target path, the routing answer, and sufficient
requirements are known, do not stop for design approval — create and validate
the Skill. When a genuinely necessary input is missing, ask for it.

The answer gates two mutually exclusive branches; creating or updating a Skill
performs no identity or profile operations of its own.

## Plain branch (answer: no)

Build the base Skill first. On Codex, invoke `$skill-creator` when available;
otherwise follow [references/portable-skill-standard.md](references/portable-skill-standard.md)
with native tools. Other platforms use that standard.

Whatever initializer produced it, `SKILL.md` frontmatter must satisfy this
project's contract: `name` equals the folder name and `description` begins
with `Use when`. No other key — including `interface` or `display_name` — may
appear there; the official validator rejects any unknown field, so a generated
`interface:` block fails.

When the user's wording names the Skill differently from the folder, keep the
folder name as `name`. If you create `agents/openai.yaml`, put the requested
display name there as `interface.display_name` only — never write `interface`
or `display_name` into SKILL.md frontmatter. If no adapter is created, omit
`display_name`. Never rename the folder to match the prose.

A plain Skill must not contain `references/profile-contract.md`,
`schemas/profile-capability.json`, or `tests/test_profile_contract.py`, and it
must not mention profile events. Do not create the `agents/openai.yaml`
adapter unless the target platform uses it.

Validate in plain mode and stop:

```text
python scripts/validate_profile_skill.py --mode plain <resolved-target-skill-dir>
```

## Profile branch (answer: yes)

1. Create or update the ordinary Skill exactly as in the plain branch.
2. Read [references/profile-authoring-standard.md](references/profile-authoring-standard.md)
   and follow its decision record: target directory, safe domain, dimensions,
   and observable evidence rules.
3. Read [references/submit-event-runtime.md](references/submit-event-runtime.md)
   and reuse its envelopes, receipts, and fail-closed rules verbatim; never
   invent storage or write profile files directly.
4. Add exactly three artifacts: `references/profile-contract.md`,
   `schemas/profile-capability.json`, and `tests/test_profile_contract.py`,
   plus a minimal `SKILL.md` link to the contract. Create `agents/openai.yaml`
   only when the target platform uses it; the core contract must not depend on
   it.

Validate in profile mode and run the generated contract tests as a forward test; they must execute and cover capability preflight/fail-closed, user consent, immutable evidence, and full scan with preservation — a placeholder test is rejected:

```text
python scripts/validate_profile_skill.py --mode profile <resolved-target-skill-dir>
```

The directory argument is always the user's resolved target path, never a
default location.
