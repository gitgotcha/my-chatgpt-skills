# Google Drive 运行时存储约定

运行时通过已授权的 Google Drive 连接器读写。根目录必须由本次会话确认，或由独立任务提示显式给出；通用 Skill 不硬编码个人文件 ID。

所有新写入使用创建文件操作与唯一文件名；**禁止调用任何“更新文件内容”的接口**。不得覆盖、追加、删除或移动旧版 `user-index.json`、`event-log.jsonl`、`profile/current/*`、`profile/history/*`。JSON 使用 UTF-8。

初始化时先验证根目录，再创建 `user-registry/`、`users/<userId>/` 及 `events`、`profile/snapshots`、`practice`。创建 `identity.json` 和 `registration-<userId>.json` 后分别读回并校验 `schemaVersion: 1.2`、`userId`、`username` 与父目录；两者都成功才绑定对话。迁移时可只读校验旧 `1.0`/`1.1` 身份锁，不得覆盖它。

每次答疑写入前先读回身份锁并列出事件目录；已存在相同 `eventKey` 时不再创建。新的 `event-<eventId>.json` 读回失败返回 `cloud_persistence_pending`。事件读回成功后，用全部去重事件创建唯一快照；快照读回失败返回 `profile_cache_pending`，并在下次读取时重建缓存。

读取时校验每条事件和快照的身份、schema 与父目录。重复事件保留文件创建时间最早的有效记录，快照只有覆盖全部有效事件键时才可使用。Google Drive 没有 ETag/If-Match 条件更新并不影响该模型：并发请求各自创建事件，后续读取会从完整事件集合重建快照。
