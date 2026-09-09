# Cloud task router

Read exactly one workflow before responding:

- LeetCode、算法、动态规划、回溯、代码复杂度：`algorithm-learning/SKILL.md`
- Java 后端模拟面试：`conducting-java-backend-mock-interviews/SKILL.md`
- 面试记录复盘、报告或画像更新：`reviewing-java-backend-interviews/SKILL.md`
- 简历驱动的 Java 后端八股学习与每日练习：`java-knowledge-based-on-resume-learn-skill/SKILL.md`
- 儿童摄影创作（开发者样本学风格、背景/主题/元素编辑、批量处理、人物不失真）：`child-photography-editing/SKILL.md`
  工作流先由开发者样本学习风格，再批量处理，同时保持人物不失真。
- 学习软件项目、源码、需求、架构、开发方案或项目面试：`software-project-learning/SKILL.md`
- 显式创建或更新可复用 Skill（仅显式调用，不隐式触发）：`profile-aware-skill-creator/SKILL.md`

## Persistence contract

All cross-session identity, profile reads and business-event writes use the one
`reliable-drive-sync` MCP tool, `submit_event`. Skills never access Drive, D1,
R2 or remote HTTP directly and never construct storage paths.

RDS V2 callers first send `{"storageVersion":2,"operation":"capabilities"}`
and then `user.resolve` to verify the display name against the account bound to
the server credential. They must not register or switch users. Personalized
reads use `projection.read`, keep one `revision` across every page and restart
pagination after `cursor_expired` or `projection_changed`. A missing or building
projection is not evidence of zero mastery.

Business writes keep the existing schema-1.2 envelope and immutable
`requestId`, `eventId`, `eventKey` and content. New facts first enter the V2
SQLite Outbox, then `/v2/events` commits them to D1; Queue consumers update
projections and archive to Drive asynchronously. Receipts have separate stages:

- local `pending` confirms only local durable queuing;
- `d1_committed` confirms D1 accepted the event;
- `projected` confirms the relevant projection applied it;
- `archived` confirms that event reached Drive.

Use `event.status` with exactly one original request or event ID to check those
later stages. Never infer projection or Drive completion from D1 acceptance,
never create polling events, and never change identifiers to hide a conflict.
Generic learning evidence uses `profile.evidence.recorded`; record only explicit
answers, completion or blockers, and never upload source repositories, private
files or identifiable child-photo content by default.

`algorithm-learning`, `software-project-learning`,
`child-photography-editing`, `conducting-java-backend-mock-interviews`,
`profile-aware-skill-creator` and `reviewing-java-backend-interviews` follow the
shared `references/rds-v2-runtime.md` contract. The profile domain for project
learning remains `backend-project-learning` to preserve continuity across the
skill rename.

## V1 compatibility

`java-knowledge-based-on-resume-learn-skill`, the repository's embedded V1
Worker/MCP implementation and historical migration material remain unchanged
until separately migrated. `cloud-mcp/` is frozen compatibility code. Legacy
V1 namespaces include `system`, `algorithm`, `interview` and `resume-knowledge`;
V1 uses NFKC name normalization and `system.user-registered` to bind `userId`.
These legacy registration rules do not apply to V2 credential-bound callers.
The business event `algorithm.learning.completed` remains unchanged.
data is read-only; `system.legacy-migration-requested` still requires a dry-run
and explicit approval. Local interview JSON and Word files under
`outputs/interview/<userId>/` are portable outputs, not profile inputs and are
never uploaded automatically.
