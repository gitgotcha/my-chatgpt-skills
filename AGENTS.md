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

RDS-JBryon is the only active persistence service. It is single-user for
乔炳源; Skills do not resolve, register, or switch accounts. All reads and
writes go through the `rds` MCP tool using readable paths such as
`project/12306` and `knowledge/java/jvm`. The shared contract is
[`references/rds-jbryon-runtime.md`](references/rds-jbryon-runtime.md).

Skills never call Drive, D1, R2, remote HTTP, or retired MCP tools directly.
Users provide readable paths, not UUIDs, node IDs, workspace epochs, or request
IDs. Before creating a new top-level domain or ambiguous path, show the complete
proposed path and get confirmation; an explicit request to create that path is
confirmation. Keep each Skill's existing evidence and privacy boundaries.

For reads, walk the route from the root with `kind=query` and `directory.list`,
passing each returned `nodeId` as the next `parentId`; match full path segments
exactly and finish pagination before choosing a node. Do not use
`directory.resolve` for missing paths. Then read the snapshot and current
revision. For writes, use `kind=request` with the current
workspace epoch, a new request ID, and the smallest patch against the observed
revision. Reuse the exact same request ID and content for an uncertain retry.
Only an authoritative `projected` status proves that the snapshot is readable;
local queuing or database acceptance is not a completed save. Preserve both
sides of a same-field conflict and ask the user to choose. The exact tool
contract, request shape, and failure behavior live in the shared reference.

Historical V1/RDS-V2 plans and reports are non-executable records only. They
must not be linked by active Skills as runtime instructions. No old Worker,
shared database, queue, or legacy MCP remains an active persistence route.
