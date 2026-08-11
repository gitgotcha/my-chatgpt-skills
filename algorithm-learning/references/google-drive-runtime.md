# Google Drive 运行时存储约定

运行时通过已授权的 Google Drive 连接器读写。根目录必须由本次会话确认，或由独立任务提示显式给出；通用 Skill 不硬编码个人文件 ID。

初始化时先验证根目录，再创建 `users/<userId>/` 及 `events`、`profile/current`、`profile/history`、`practice`。创建并读回 `identity.json` 与初始 `profile-snapshot.json` 后才视为建档成功。

更新前读取目标文件元数据与内容，核验 `userId`、`username`、`profileVersion` 和父目录；同名文件先核对用途/ID，禁止盲目覆盖。JSON 使用 UTF-8。事件日志只追加经 `eventKey` 去重的行；连接器不支持安全替换时返回 `cloud_persistence_pending`，不能把本地缓存说成云端已保存。
