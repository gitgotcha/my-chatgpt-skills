# 独立每日任务模板

固定时区：Asia/Shanghai。不要求姓名或账户信息。

计划：

```ical
BEGIN:VEVENT
DTSTART:20260101T090000
RRULE:FREQ=DAILY
END:VEVENT
```

运行提示词：使用 algorithm-learning Skill 的每日练习协议，从 knowledge/algorithm-learning/学习快照.json 读取今天的练习历史；按 Asia/Shanghai 生成题单。跨会话读取与保存只通过 rds MCP；没有读取到快照时如实说明，不推断掌握度。用户反馈后追加事实，不覆盖已有题单或原答案。
