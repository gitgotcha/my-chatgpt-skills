# 算法画像数据契约

协议版本为 **schemaVersion `1.2`**。`userId` 是唯一主键；`username` 是展示名与二次校验字段，不能替代主键。用户详情仅在 `users/<userId>/` 内读写，**不可跨用户读取**。

## 规范目录

唯一规范根是 `DriveRoot/my-chatGPT-skills/`。算法领域只使用下列目录：

```text
DriveRoot/my-chatGPT-skills/
├── user-registry/
│   └── registration-<userId>.json
└── users/<userId>/
    ├── identity.json
    └── algorithm/
        ├── events/
        │   └── event-<eventId>.json
        ├── profile/snapshots/
        │   └── snapshot-<UTC>-<headEventId>.json
        └── plans/daily/
            └── daily-plan-YYYY-MM-DD-<planId>.json
```

等价的完整路径：

```text
my-chatGPT-skills/user-registry/registration-<userId>.json
my-chatGPT-skills/users/<userId>/identity.json
users/<userId>/algorithm/events/
users/<userId>/algorithm/profile/snapshots/
users/<userId>/algorithm/plans/daily/
```

写入路径一律由 Cloud MCP Worker 按上述父子链构造。Skill、每日任务模板和辅助脚本只调用 `submit_event`，
不得自行拼路径，也不得把任何内容写入旧 namespace 目录。

下列旧文件保留作为只读兼容数据，禁止再写入：旧 namespace 级注册索引、JSONL 事件日志，以及旧快照目录下的历史快照文件。任何新建 JSON 均重复 `schemaVersion`、`userId`、`username`；读回时还必须校验文件父目录。

## 注册记录与身份锁

`user-registry/registration-<userId>.json` 是全局注册表中唯一允许读取的跨用户数据，只含：

```json
{
  "schemaVersion": "1.2",
  "userId": "uuid",
  "username": "乔炳源",
  "status": "active",
  "createdAt": "2026-08-11T10:23:11.873Z"
}
```

注册成功后才读取对应 `identity.json`。姓名只做机械标准化（Unicode NFKC 与去除首尾空白）：命中唯一用户时复用其 `userId`；不存在时创建稳定独立的新 `userId`；存在无法消解的同名冲突时停止并要求人工选择，不可覆盖或静默选择。

新建 `identity.json` 使用 `schemaVersion: "1.2"`。为迁移既有档案，可只读校验 `1.0` 或 `1.1` 身份锁的 `userId`、`username` 与父目录，并使用新的 1.2 注册、事件和快照文件；不得为迁移覆盖旧身份锁。

## 学习事件：唯一事实来源

每个事件独占一个 `users/<userId>/algorithm/events/event-<eventId>.json` 文件：

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

快照是缓存，不是事实来源。Worker 每次重建都创建 `users/<userId>/algorithm/profile/snapshots/snapshot-<UTC>-<headEventId>.json`：

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

不维护 `profileVersion`、`appliedEventKeys` 或表示“当前快照”的指针文件。读取时只采用 `sourceEventKeys` 覆盖全部已知有效事件的最新有效快照；没有覆盖完整事件集的快照、字段不符的快照或身份不符的快照均忽略，并由全部去重事件重建。

快照只能由 Worker 从已验证事件物化，不接受 Skill 直接上传或覆盖；任何快照都应可以从原始事件重建。

## 写入、恢复与状态

1. 调用 `submit_event` 时先按姓名解析或注册用户，锁定 `userId` 与规范化 `username`。
2. 列出、校验并按 `eventKey` 去重全部事件。
3. 本地 `submit_event` 先写 SQLite；D1 Outbox 接收后返回 `deliveryState: "cloud_accepted"`，未接收时返回 `pending`。两者都不等于 Drive 读回完成。
4. QStash/Worker 异步创建唯一事件文件，再从完整事件集创建快照；Skill 不等待该内部状态。
5. 同一 `requestId` 的重试由 SQLite 与 D1 Outbox 幂等处理，不重复追加事件。
6. 任何写入失败都不得回退到旧 namespace 目录，也不得让 Skill 直接调用 Drive。

## 题单与打卡

题单是 `users/<userId>/algorithm/plans/daily/daily-plan-YYYY-MM-DD-<planId>.json` 的一次性创建文件。每道题有稳定 `itemId`、来源（`Hot100|代码随想录|variant`）、题目链接、专题、难度、角色（`weakness-review|current-topic|integrated-variant|carry-over`）和状态。打卡只新建事件，不覆盖题单或直接修改掌握度。
