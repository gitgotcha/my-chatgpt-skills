# 独立每日任务模板

身份锁：

```text
userId: <USER_UUID>
username: <USERNAME>
Drive root: <CONFIRMED_GOOGLE_DRIVE_FOLDER_URL>
timezone: Asia/Shanghai
```

计划：

```ical
BEGIN:VEVENT
DTSTART:20260101T090000
RRULE:FREQ=DAILY
END:VEVENT
```

运行提示词：读取上述 Drive 根目录中 `users/<USER_UUID>/` 的 identity、current snapshot、事件日志和最近题单。严格核对 userId 与 username。按 `algorithm-learning` Skill 的每日练习协议汇总未应用事件、更新镜像，并生成今天的 3～5 题练习包；优先保留未完成题。任何必要 Drive 读写、身份或版本校验失败时不生成题单、不更新镜像，报告 `cloud_persistence_pending`，等待次日重试。不要使用聊天上下文，不得读取 `user-index.json`，也不要访问其他用户目录。
