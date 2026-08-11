# Google Drive 运行时存储约定

运行时通过已授权的 Google Drive 连接器读写。根目录必须由本次会话确认，或由独立任务提示显式给出；通用 Skill 不硬编码个人文件 ID。

对话级身份门禁只可读取根目录的 `user-index.json` 枚举 `{userId, username, status, createdAt}`；选中用户后必须读取其 `identity.json` 再绑定。新建时，先创建 `users/<userId>/` 及 `events`、`profile/current`、`profile/history`、`practice`，创建并读回 `identity.json` 与初始 `profile-snapshot.json`，最后创建或更新索引项；任何一步失败均回报未建档，不得绑定。

更新前读取目标文件元数据与内容，核验 `userId`、`username`、`profileVersion` 和父目录；同名文件先核对用途/ID，禁止盲目覆盖。JSON 使用 UTF-8。每次学习请求结束前，事件日志只追加经 `eventKey` 去重的行，随后写入并读回历史快照，再用乐观锁替换 current 快照。连接器不支持安全替换、任何读回校验失败或出现版本冲突时，返回 `cloud_persistence_pending` 或 `profile_conflict`，不能把本地缓存说成云端已保存。
