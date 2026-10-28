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

Validate in plain mode:

```text
python scripts/validate_profile_skill.py --mode plain <resolved-target-skill-dir>
```

## Profile branch (answer: yes)

1. Create or update the ordinary Skill as in the plain branch.
2. Follow the decision record in [references/profile-authoring-standard.md](references/profile-authoring-standard.md): target directory, readable nested route, dimensions, and observable evidence. The taxonomy `domain` field is not the persistence path.
3. Read the shared [RDS-JBryon runtime contract](../references/rds-jbryon-runtime.md) and define the Skill's readable route plus JSON snapshot shape. The only supported persistence backend is the single-user `rds` MCP. Do not generate account identity resolution, UUID binding, event projection, or direct file/Drive storage.
4. Add exactly three artifacts: `references/profile-contract.md`, `schemas/profile-capability.json`, and `tests/test_profile_contract.py`, plus a minimal `SKILL.md` link. Create `agents/openai.yaml` only when the target platform uses it.

Validate in profile mode and run generated contract tests as a forward test; they must cover capability/path preflight and fail-closed behavior, explicit route confirmation when required, snapshot reads and minimal revision-based patches, and preservation of original evidence — placeholder tests are rejected:

```text
python scripts/validate_profile_skill.py --mode profile <resolved-target-skill-dir>
```

The directory argument is always the user's resolved target path, never a
default location.

## RDS-JBryon 接入

生成需要跨会话状态的 Skill 时，必须遵循共享 [RDS-JBryon 运行契约](../references/rds-jbryon-runtime.md)，并将状态建模为用户可读路径下的 JSON 快照。用户只提供路由名称，不提供账户身份、UUID、nodeId 或 workspace epoch。新顶层目录或含义不明确的路由先展示完整路径并取得确认。Skill 只调用 `rds` MCP，不得调用已退役的 `reliable_drive_sync`、账户解析、事件投影或直接 Drive/D1/HTTP。普通 Skill 创建不产生用户学习记录。
