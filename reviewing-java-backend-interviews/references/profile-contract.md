# 共享画像协议

协议版本为 `schemaVersion: "1.2"`，Schema 位于 `schemas/contracts.schema.json`。唯一活动主键是全局 `userId`，它由 `submit_event` 按姓名从 `user-registry/` 解析或创建。旧的候选人索引、候选人目录与候选人锁模型已废弃，只允许出现在 legacy 适配器或带 archived/superseded 标记的历史文档中。

## 画像的唯一实现方

画像 reducer 的唯一活动实现是 Cloud MCP Worker 的 `cloud-mcp/src/profile-model.js`。Python 侧（`scripts/interview_core.py`）不再实现画像校验、乐观 current-profile 更新或事件重放。它只负责：

- 构造并校验 schema-1.2 `interview.review.completed` 事件；
- 写入本地报告副本；
- 提供与云端无关的领域解析和题源规划纯函数。

## 快照结构

快照由 Worker 物化到 `users/<userId>/interview/profile/snapshots/`，是事件的派生结果，不接受技能直接上传或覆盖。快照必含：

```text
schemaVersion      "1.2"
userId             全局用户 ID
username           规范化姓名
generatedAt        UTC 时间戳
headEventId        最新已应用事件的 eventId
sourceEventKeys    参与本次重建的全部事件键
domainProfiles     按领域隔离的技术弱点
generalCompetencies 跨领域累计的通用能力
```

## 重建规则

1. 只使用已验证的 `interview.review.completed` 事件，且 `applyProfileChanges === true`。
2. 同一 `sessionId` 只保留 `reviewVersion` 最大的事件；修正产生新的不可变版本，不额外复制旧 Review。
3. 身份元数据取自任一已验证事件，因此 `applyProfileChanges: false` 的复盘不会丢失用户绑定。
4. 弱点状态由 `outcome` 推导：失败置 `open`；通过累计 `passingSessionIds` 与 `passingVariantIds`，两者都达到 2 个才置 `closed`，否则为 `improving`。
5. 未识别到 `weaknessId` 的变化落入 `generalCompetencies`，状态为 `needs_work` 或 `demonstrated`。

任何快照都应能从原始事件重建。事件已存在而快照缺失时，用同一幂等键重试只补做投影，不重复追加事件。
