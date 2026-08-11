# 算法画像数据契约

协议版本 `1.1`。`userId` 是唯一主键；`username` 是全局唯一的展示名与二次校验字段，不能替代主键。用户详情仅在 `users/<userId>/` 内读写，**不可跨用户读取**。

## 云端目录

```text
algorithm/
  user-index.json
  users/<userId>/
    identity.json
    events/event-log.jsonl
    profile/current/profile-snapshot.json
    profile/history/profile-v<N>.json
    practice/daily-plan-YYYY-MM-DD.json
```

`user-index.json` 仅含 `{schemaVersion, users:[{userId, username, status, createdAt}]}`，仅允许为列出用户而读取；它不得包含题目、事件、掌握度、弱点或打卡信息。除对话身份门禁读取索引外，任何流程都不可跨用户读取。`identity.json` 含 `schemaVersion`、`userId`、`username`、`createdAt`。其余所有 JSON 均重复 `userId`、`username` 与 `schemaVersion`；任何不一致都终止操作。

## 对话身份绑定

新对话先暂存第一条学习请求，再从 `user-index.json` 列出 active 用户供选择。选中条目后必须读取对应 `identity.json` 并核对 `{userId, username}`，成功才绑定本对话。新建用户只在 username 唯一时生成 UUID，并在 identity、初始快照和索引均创建且读回成功后绑定。同一对话沿用绑定；只有“切换用户”“重新验证身份”或“我不是刚才那个人”才清空绑定并重新选择。

## 学习事件

每行 `event-log.jsonl` 是不可变的 `LearningEvent`：

```json
{
  "schemaVersion": "1.1",
  "eventId": "evt-uuid",
  "eventKey": "userId:sourceId:topic:observedAt",
  "userId": "uuid",
  "username": "name",
  "observedAt": "ISO-8601",
  "source": "qa|checkin|daily-plan",
  "topic": "滑动窗口",
  "problem": {"title": "最小覆盖子串", "source": "Hot100", "url": ""},
  "evidence": "明确错误或用户陈述的摘要",
  "outcome": "incorrect|stuck|partial|completed|correct|consulted",
  "tags": ["边界", "窗口收缩"],
  "confidence": "high"
}
```

同一 `eventKey` 只能应用一次。`outcome=correct` 也应记录，防止画像只积累负面证据。`outcome=consulted` 仅记录本次主题，不得新增弱点。

## 镜像快照与版本

`profile-snapshot.json` 必含 `profileVersion`、`headEventId`、`generatedAt`、`currentTopic`、`topicMastery`、`weaknesses`、`pendingProblemIds` 和 `appliedEventKeys`。每次学习请求结束前都先读当前快照，基于未应用事件在内存计算新版本，保存历史快照，再替换 current；若 `profileVersion` 与预期不同，返回 `profile_conflict`，不得覆盖。

弱点记录包含 `id`、`topic`、`skill`、`severity`（low/medium/high）、`evidenceEventIds`、`lastSeenAt`、`resolvedEvidenceCount`。只有两个不同日期、不同题目且 `correct` 的高置信证据，才将该弱点标为 `resolved`。

## 题单与打卡

每日题单含 `planId`、`date`、`profileVersionUsed`、`items`、`carryOverProblemIds` 与 `status`。每道题有稳定 `itemId`、来源（`Hot100|代码随想录|variant`）、题目链接、专题、难度、角色（`weakness-review|current-topic|integrated-variant|carry-over`）和状态。打卡只更新题单状态并新增事件，不能直接修改掌握度。
