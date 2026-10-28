# 算法学习快照字段

算法状态保存在 `knowledge/algorithm-learning/学习快照.json`，读写方式遵守 [RDS-JBryon 运行契约](../../references/rds-jbryon-runtime.md)。数据只是 JSON 内容，不是 RDS 事件 DTO。

```json
{
  "schemaVersion": "algorithm-learning-snapshot/1",
  "records": [{
    "recordId": "tool-generated-or-stable-key",
    "topic": "双指针",
    "problem": {"title": "三数之和", "source": "Hot100"},
    "evidence": "用户请求讲解三数之和。",
    "outcome": "consulted",
    "tags": ["排序", "双指针", "去重"],
    "studiedAt": "ISO-8601"
  }],
  "dailyPlans": []
}
```

只记录明确观察到的错误、未掌握、完成或用户主动打卡事实；没有掌握度证据时使用中性的 `consulted`。不得臆测弱点、评分或完成状态。每日题单追加保存，不覆盖用户原答案或旧题单。
