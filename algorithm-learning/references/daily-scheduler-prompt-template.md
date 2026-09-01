# 独立每日任务模板

身份输入：

```text
username: <USERNAME>
timezone: Asia/Shanghai
```

计划：

```ical
BEGIN:VEVENT
DTSTART:20260101T090000
RRULE:FREQ=DAILY
END:VEVENT
```

运行提示词：使用 `algorithm-learning` Skill 的每日练习协议，为 `<USERNAME>` 生成今天的算法练习。按姓名调用 `submit_event` 解析或注册用户，只提交 `algorithm.daily-plan-created` 等事件；事件先进入 SQLite 与 D1 Outbox，再由 Worker 异步写入规范目录 `users/<userId>/algorithm/`。不要使用聊天上下文，不要读取或写入其他用户目录，也不要自行读写云端文件。回执为 `cloud_accepted` 时只报告“已进入云端队列”，为 `pending` 时报告“已在本机排队”，不得宣称 Drive 或画像已同步。
