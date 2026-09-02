---
name: profile-aware-skill-creator
description: Use when a user explicitly asks to create or update a reusable Skill and wants to decide whether it should read and update a persistent cross-session user profile.
---

# Profile-Aware Skill Creator

Create or update a Skill at the path the user explicitly named. The user's
target path is authoritative: never redirect output to a default skills
directory, the current repository, or a temporary folder. **The named
directory is the Skill root**: write `SKILL.md` and every other generated file
directly into it, never into a nested subdirectory named after the Skill. If
no path was given, ask for one and stop. When the target directory already
exists, inspect its contents first and preserve every unrelated file, field,
and user modification; update in place with the smallest additive change.

## Ask the single routing question

If the current request does not already state the answer, ask exactly one
question before creating anything: does this Skill need to save and read a
person profile across sessions? Honor an answer that is already explicit —
never re-ask, and never decide for the user. That routing question is the only
question you may ask. Do not stop to request design approval or any other
go-ahead; create the Skill and validate it, and never end a turn on a question
once the path and the routing answer are known.

The answer gates two mutually exclusive branches. Creating or updating a Skill
performs no identity or profile operations of its own.

## Plain branch (answer: no)

Build the ordinary Skill first. On Codex, invoke `$skill-creator` when it is
available; otherwise follow [references/portable-skill-standard.md](references/portable-skill-standard.md)
with native file tools. Other platforms use the portable standard directly.

Whichever initializer produced it, the final `SKILL.md` frontmatter must
satisfy this project's contract: `name` equals the Skill folder name, and
`description` begins with `Use when`. When the user's wording names the Skill
differently from the folder, keep the folder name as `name` and carry the
requested name in `interface.display_name`; never rename the folder to match
the prose.

A plain Skill must not contain `references/profile-contract.md`,
`schemas/profile-capability.json`, or `tests/test_profile_contract.py`, and it
must not mention profile events. Do not create the `agents/openai.yaml`
adapter unless the target platform uses it.

Validate the result in plain mode and stop:

```text
python scripts/validate_profile_skill.py --mode plain <resolved-target-skill-dir>
```

## Profile branch (answer: yes)

1. Create or update the ordinary Skill exactly as in the plain branch.
2. Read [references/profile-authoring-standard.md](references/profile-authoring-standard.md)
   and follow its authoring decision record: resolved target directory, safe
   domain choice, dimensions, and observable evidence rules.
3. Read [references/submit-event-runtime.md](references/submit-event-runtime.md)
   and reuse its envelopes, receipts, and fail-closed rules verbatim; never
   invent a storage mechanism or write profile files directly.
4. Add exactly three artifacts to the target Skill:
   `references/profile-contract.md`, `schemas/profile-capability.json`, and
   `tests/test_profile_contract.py`, plus a minimal link from the target
   `SKILL.md` to its profile contract. Create `agents/openai.yaml` only when
   the target platform uses it, and never let the core contract depend on it.

Validate the result in profile mode, run the generated contract tests as a
forward test, and stop:

```text
python scripts/validate_profile_skill.py --mode profile <resolved-target-skill-dir>
```

The directory argument is always the user's resolved target path, never a
default location.
