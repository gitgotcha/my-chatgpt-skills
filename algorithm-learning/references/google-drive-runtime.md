# Google Drive 运行时存储约定

Google Drive 只作为最终存储层，由已授权的 Cloud MCP Worker 访问。Skill 本身、每日任务模板和辅助脚本都不读取或写入 Drive：所有持久化数据只通过 `submit_event` 提交。

运行时根目录必须由本次会话确认，或由独立任务提示显式给出；通用 Skill 不硬编码个人文件 ID。

所有新写入使用创建文件操作与唯一文件名；**禁止调用任何“更新文件内容”的接口**。不得覆盖、追加、删除或移动旧版注册索引、事件日志与历史快照文件。JSON 使用 UTF-8。

写入一律落在唯一规范根 `DriveRoot/my-chatGPT-skills/` 下：`user-registry/` 保存全局注册，
`users/<userId>/` 保存身份与 `algorithm/`、`interview/`、`resume-knowledge/` 三个领域目录。
领域子目录按首次物化需要创建，不要求预先建立空目录。

初始化时先验证根目录，再创建用户目录与需要的领域目录。创建 `identity.json` 和
`registration-<userId>.json` 后分别读回并校验 `schemaVersion: 1.2`、`userId`、`username` 与父目录；两者都成功才视为注册完成。迁移时可只读校验旧 `1.0`/`1.1` 身份锁，不得覆盖它。

每次答疑写入前先解析或注册用户并列出事件目录；已存在相同 `eventKey` 时不再创建。新的 `event-<eventId>.json` 读回失败返回 `cloud_persistence_pending`。事件读回成功后，Worker 用全部去重事件创建唯一快照；快照读回失败返回 `profile_cache_pending`，并在下次读取时重建缓存。

读取优先使用规范目录；规范目录缺失时才由只读兼容器回退到旧 namespace 目录。任何写入失败都不得回退到旧路径。

读取时校验每条事件和快照的身份、schema 与父目录。重复事件保留文件创建时间最早的有效记录，快照只有覆盖全部有效事件键时才可使用。Google Drive 没有 ETag/If-Match 条件更新并不影响该模型：并发请求各自创建事件，后续读取会从完整事件集合重建快照。
