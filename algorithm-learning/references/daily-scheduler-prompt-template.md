# 独立每日任务模板

运行参数：

```text
timezone: Asia/Shanghai
```

计划：

```ical
BEGIN:VEVENT
DTSTART:20260101T090000
RRULE:FREQ=DAILY
END:VEVENT
```

运行提示词：使用 `algorithm-learning` Skill 的每日练习协议，先通过 `submit_event(account.current)` 核验当前设备账户，再为该账户生成今天的算法练习。后续业务请求携带完整 `bindingContext`，只提交 `algorithm.daily-plan-created` 等事件；所有事件与题单由 Worker 写入规范目录 `users/<userId>/algorithm/` 下的事件、画像快照与 `plans/daily/` 目录。不要使用姓名或聊天上下文恢复授权，不要读取或写入其他用户目录，也不要自行读写云端文件。任何授权或写入失败时不生成题单、不宣称已同步画像，按回执报告待处理状态，等待下次重试。
