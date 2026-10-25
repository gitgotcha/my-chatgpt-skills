# RDS V1/V2 兼容与数据清理边界

本文面向维护 Skills、MCP 调用契约和迁移文档的贡献者。它说明代码兼容关系，不是生产环境实时盘点，也不授权删除任何用户数据。

## 结论

新 Skill 的持久化接口应遵循仓库的共享 V2 契约：通过唯一 MCP 工具 `submit_event` 调用能力检查、身份核对、投影读取和事件写入。V1 注册规则、直接访问 Drive/D1 或旧路径读取不能作为新 Skill 的实现方式。

V1 写入退役与所有 V1 兼容代码/历史文件清除是不同工作。当前上游 Worker 生产配置关闭 V1 写入并标记 V1 retired，但仍保留有限的旧事件只读回退和迁移复制能力。只要这些代码还在，删除旧数据就可能影响未迁移历史事件或迁移来源；不能因 V2 可以独立接收新事件而推断旧数据可直接删除。

## 兼容行为

| 领域 | 当前行为 | 对 Skill 和仓库维护的要求 |
| --- | --- | --- |
| 新调用 | V2 通过 credential-bound identity、`projection.read` 和 `submit_event` 契约工作 | 新 Skill 复用共享 `references/rds-v2-runtime.md`；不要新增 V1 注册、V1 写入或直接存储访问 |
| V1 Worker 接口 | 上游生产配置将 V1 标记为 retired 并关闭 V1 写入 | 配置文件只代表仓库中的配置；没有线上部署核验证据时，不要把它写成实时生产状态 |
| 旧事件读取 | 上游事件存储优先读规范目录；仅当规范事件目录不存在时，才对 `algorithm`、`interview` 回退到旧事件目录 | 旧目录仍可能是历史事件的唯一来源；删除前须确认目标用户和 domain 的迁移/读取需求 |
| 旧数据迁移 | 迁移器扫描旧注册表、事件和画像快照；dry-run 生成计划，execute 只复制缺失对象并校验内容哈希，来源不更新、不移动、不删除 | 迁移完成不等于源文件已退役；需要独立的数据保留与删除决定 |
| V1 D1 数据 | 仓库内的历史切换记录只能说明当时执行的清理范围 | 先读 schema 并对精确表做当前只读盘点；绝不按猜测删除 `rds2_*`、迁移历史或未知表 |

## 删除前的核验门

1. 核对实际部署版本、V1 开关和定时任务；本仓库或上游仓库里的配置文件不能单独证明线上状态。
2. 对明确的用户、domain、表或 Drive 目录做只读盘点，区分已迁移、未迁移、冲突和无法验证的数据，并先准备可恢复备份。
3. 确认需要保留的旧事件已在规范目录可读，迁移计划没有未处理项，且活跃客户端不再依赖旧目录回退。
4. 列出精确删除对象并单独评审。保留 V2 `rds2_*` 表、迁移历史和未知对象；Drive 操作不得针对共享根目录递归清除。
5. 清理后复查实际删除范围和 V2 读写；记录操作者、时间、备份和结果。

证据不足时保留源数据并继续只读盘点。测试通过、历史 runbook 或“V1 retired”都不能替代当前数据核验。

## 上游代码证据

以下链接固定到此次审计的上游 Worker 基线 `553489dd86a9d75ed977ec23a8aea84000d05878`，用于解释具体代码，不表示该 commit 当前仍部署在线上：

- [生产配置：V1 开关与 V2 恢复 cron](https://github.com/gitgotcha/my-chatgpt-mcp/blob/553489dd86a9d75ed977ec23a8aea84000d05878/services/reliable-drive-sync-worker/wrangler.production.toml)
- [Worker：V1 retired 路由与 scheduled 行为](https://github.com/gitgotcha/my-chatgpt-mcp/blob/553489dd86a9d75ed977ec23a8aea84000d05878/services/reliable-drive-sync-worker/src/index.js)
- [事件存储：规范目录优先及旧事件回退](https://github.com/gitgotcha/my-chatgpt-mcp/blob/553489dd86a9d75ed977ec23a8aea84000d05878/services/reliable-drive-sync-worker/src/event-store.js)
- [旧数据适配器：只读域与目录限制](https://github.com/gitgotcha/my-chatgpt-mcp/blob/553489dd86a9d75ed977ec23a8aea84000d05878/services/reliable-drive-sync-worker/src/legacy-reader.js)
- [迁移存储：复制、哈希校验与不删除来源](https://github.com/gitgotcha/my-chatgpt-mcp/blob/553489dd86a9d75ed977ec23a8aea84000d05878/services/reliable-drive-sync-worker/src/migration-store.js)
- [历史切换记录：带日期的执行证据](https://github.com/gitgotcha/my-chatgpt-mcp/blob/553489dd86a9d75ed977ec23a8aea84000d05878/docs/runbooks/2026-09-08-full-v2-cutover.md)

仓库内各 Skill 的具体接口仍以共享 [RDS V2 运行契约](../algorithm-learning/references/rds-v2-runtime.md) 为准。
