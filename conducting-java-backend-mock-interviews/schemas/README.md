# 共享 JSON Schema

此目录是 interviewing 协议的受测试副本，与 `reviewing-java-backend-interviews/schemas/` 保持字节一致。它只描述当前 schema-1.2 的按姓名解析身份、用户注册、会话事件与复盘事件结构，用于用户解析、模拟会话固化和复盘交接；不实现复盘或画像更新。

`manifest.json` 只列出当前仍在使用的 schema-1.2 定义：

```text
Identity, Registration, Question, SessionEvent,
QuestionReview, ProfileChange, ReviewEvent, ProfileSnapshot
```

任何已废弃的候选人索引或候选人目录模型都不在此目录中，也不得重新引入。
