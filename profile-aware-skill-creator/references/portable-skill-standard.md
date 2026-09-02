# Portable Skill Standard

This reference defines the platform-neutral base shape of an ordinary Skill.
Read it when creating or updating the base Skill before any profile layer is
considered. The profile-specific rules live in
[profile-authoring-standard.md](profile-authoring-standard.md); the runtime
protocol lives in [submit-event-runtime.md](submit-event-runtime.md).

## Base Skill shape

A portable Skill is a directory named with a lowercase hyphenated identifier
(for example `release-notes`) containing:

```text
<target-skill>/
|-- SKILL.md            (required)
|-- references/         (optional, only when the Skill genuinely needs it)
|-- scripts/            (optional, only when the Skill genuinely needs it)
|-- schemas/            (optional, only when the Skill genuinely needs it)
`-- tests/              (optional, only when the Skill genuinely needs it)
```

`SKILL.md` is the only required file. Its YAML frontmatter contains `name`
(equal to the folder name) and a `description` that begins with `Use when` and
states when the Skill applies. Do not create README files, changelogs, empty
directories, placeholder assets, or permanent example Skills.

## Progressive disclosure

Keep `SKILL.md` short: frontmatter plus the workflow a new session needs to
start. Put heavy reference material in `references/` files and link them at the
exact decision point where they should be loaded. A session that does not hit
that decision point should never read the file.

## Target-path authority

The path the user specifies is the authoritative output location. Use it
exactly as given; never redirect output to `$HOME`, a default skills
directory, the current repository, or a temporary folder. When the parent
directory does not exist or the request's meaning is unclear, stop and ask for
an explicit path rather than guessing.

The named directory is the Skill root. Write `SKILL.md` directly into it; do
not create a nested subdirectory named after the Skill, because that silently
moves the authoritative path one level down.

## Update in place

When the target directory already exists, update it in place:

- Inspect existing `SKILL.md`, `agents/`, `references/`, `scripts/`,
  `schemas/`, and tests first.
- Preserve unrelated files, custom fields, and user modifications.
- Make the smallest additive change that satisfies the request; do not re-run
  a base initializer over the existing Skill.

## Deterministic validation

Every generated or updated Skill is validated before delivery by a
deterministic, standard-library validator invoked as:

```text
python scripts/validate_profile_skill.py --mode plain <target-skill-dir>
python scripts/validate_profile_skill.py --mode profile <target-skill-dir>
```

The mode reflects the branch chosen for that Skill. Validation is
deterministic: the same directory and mode always produce the same result.
Validation failures are fixed in the generated files, never silenced.

## Platform routing

- **Codex with `$skill-creator` available:** invoke `$skill-creator` for the
  base Skill, then apply the profile layer if the profile branch was chosen.
- **Other environments, or `$skill-creator` missing:** follow this portable
  standard with native file tools.
- **`agents/openai.yaml`** is an optional OpenAI/Codex UI adapter. It is never
  part of the core contract, and the Skill's core logic must not depend on it.
  Platforms that ignore it must lose no functionality.

Platform-specific tool-call syntax may differ, but any JSON envelope passed to
`submit_event` must be identical across Codex, ChatGPT, Claude, and
WorkBuddy. Distributable Skill files contain no personal absolute paths, home
directories, or Drive identifiers.
