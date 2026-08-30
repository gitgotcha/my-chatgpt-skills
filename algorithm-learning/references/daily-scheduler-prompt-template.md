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

运行提示词：使用 `algorithm-learning` Skill 的每日练习协议，为 `<USERNAME>` 生成今天的算法练习。按姓名调用 `submit_event` 解析或注册用户，只提交 `algorithm.daily-plan-created` 等事件；所有事件与题单由 Worker 写入规范目录 `users/<userId>/algorithm/` 下的事件、画像快照与 `plans/daily/` 目录。不要使用聊天上下文，不要读取或写入其他用户目录，也不要自行读写云端文件。任何身份解析或写入失败时不生成题单、不宣称已同步画像，报告 `cloud_persistence_pending`，等待次日重试。
