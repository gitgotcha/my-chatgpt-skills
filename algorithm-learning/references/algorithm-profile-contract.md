# 算法事件字段与 V2 画像

先遵守 [V2 运行契约](rds-v2-runtime.md)。业务事件 schemaVersion 为字符串 1.2，身份必须来自凭据核对。事件字段示例（UUID 与时间替换为实际值）：

```json
{
  "schemaVersion": "1.2",
  "eventType": "algorithm.learning.completed",
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



外层 envelope 的 namespace=algorithm，eventType=algorithm.learning.completed，payload={event}。内层必须带相同 eventType；不添加协议未定义的评分或自定义字段。事实不可变；同一事件的重试保留三个 ID 和内容。只有明确证据才判定 incorrect/stuck/partial/completed/correct；consulted 不形成弱点。

画像从 projection.read 的 algorithm/learning 获取。summary 与 entries 是 D1 当前激活代，按 nextCursor 完整分页，不列举 Drive 历史，不由 Skill 重建。缺画像或构建中时不得假称具有完整历史。每日题单使用 algorithm.daily-plan-created，打卡新增学习事件，不能覆盖题单。
