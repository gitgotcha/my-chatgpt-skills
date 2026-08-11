# 算法画像数据契约

协议版本为 **schemaVersion `1.2`**。`userId` 是唯一主键；`username` 是展示名与二次校验字段，不能替代主键。用户详情仅在 `users/<userId>/` 内读写，**不可跨用户读取**。

## 云端目录与旧文件兼容

```text
algorithm/
  user-registry/
    registration-<userId>.json
  users/<userId>/
    identity.json
    events/
      event-<eventId>.json
    profile/
      snapshots/
        snapshot-<observedAt>-<eventId>.json
    practice/
```

下列旧文件保留作为只读兼容数据，禁止再写入：`algorithm/user-index.json`、`events/event-log.jsonl`、`profile/current/profile-snapshot.json` 与 `profile/history/profile-v*.json`。任何新建 JSON 均重复 `schemaVersion`、`userId`、`username`；读回时还必须校验文件父目录。

## 注册记录与身份锁

`user-registry/registration-<userId>.json` 是新对话选择用户时唯一允许读取的跨用户数据，只含：

```json
{
  "schemaVersion": "1.2",
  "userId": "uuid",
  "username": "乔炳源",
  "status": "active",
  "createdAt": "2026-08-11T10:23:11.873Z"
}
```

选择后才读取对应 `identity.json`。新建时规范化用户名并枚举注册记录；同名并发档案返回 `username_conflict`，不可覆盖或静默选择。

新建 `identity.json` 使用 `schemaVersion: "1.2"`。为迁移既有档案，可只读校验 `1.0` 或 `1.1` 身份锁的 `userId`、`username` 与父目录，并使用新的 1.2 注册、事件和快照文件；不得为迁移覆盖旧身份锁。

## 学习事件：唯一事实来源

每个事件独占一个 `events/event-<eventId>.json` 文件：

```json
{
  "schemaVersion": "1.2",
  "eventId": "uuid",
  "eventKey": "<userId>:qa:three-sum:<ISO-8601>",
  "userId": "uuid",
  "username": "乔炳源",
  "observedAt": "2026-08-11T10:26:51.215Z",
  "source": "qa",
  "topic": "双指针",
  "problem": {"title": "三数之和", "source": "Hot100", "url": "https://leetcode.cn/problems/3sum/"},
  "evidence": "用户请求讲解三数之和。",
  "outcome": "consulted",
  "tags": ["排序", "双指针", "去重"],
  "confidence": "high"
}
```

事件永不修改、永不删除。写入前按 `eventKey` 去重；存在同键有效事件即复用，不创建第二条。读取到重复时保留文件创建时间最早的可验证记录，并报告 `duplicate_event_key`。`incorrect`、`stuck`、`partial`、`completed`、`correct` 与中性的 `consulted` 都可记录；弱点只能由有证据的非中性结果推导。

## 画像快照：可丢弃缓存

快照是缓存，不是事实来源。每次重建都创建 `profile/snapshots/snapshot-<observedAt>-<eventId>.json`：

```json
{
  "schemaVersion": "1.2",
  "userId": "uuid",
  "username": "乔炳源",
  "generatedAt": "2026-08-11T10:26:52.000Z",
  "headEventId": "uuid",
  "sourceEventKeys": ["<eventKey>"],
  "currentTopic": "双指针",
  "topicMastery": {},
  "weaknesses": [],
  "pendingProblemIds": []
}
```

不维护 `profileVersion`、`appliedEventKeys` 或 `profile/current` 指针。读取时只采用 `sourceEventKeys` 覆盖全部已知有效事件的最新有效快照；没有覆盖完整事件集的快照、字段不符的快照或身份不符的快照均忽略，并由全部去重事件重建。

## 写入、恢复与状态

1. 读取并校验身份锁；列出、校验并按 `eventKey` 去重全部事件。
2. 若没有同键事件，创建唯一事件文件并读回。事件未读回时返回 `cloud_persistence_pending`，不得称已记录。
3. 事件已读回后，重新列出事件并从完整事件集创建唯一快照；快照读回成功才可称“已同步画像”。
4. 快照创建或读回失败时返回 `profile_cache_pending`：学习事件已保存，画像将在下次读取时重建。

## 题单与打卡

题单仍是 `practice/daily-plan-YYYY-MM-DD-<planId>.json` 的一次性创建文件。每道题有稳定 `itemId`、来源（`Hot100|代码随想录|variant`）、题目链接、专题、难度、角色（`weakness-review|current-topic|integrated-variant|carry-over`）和状态。打卡只新建事件，不覆盖题单或直接修改掌握度。
