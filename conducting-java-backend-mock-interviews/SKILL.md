---
name: conducting-java-backend-mock-interviews
description: Use when conducting a Java backend mock interview for a user resolved by display name, with one immutable submit_event handoff.
---

# Java 后端模拟面试


先读 [RDS V2 运行契约](references/rds-v2-runtime.md)。唯一远端工具为 submit_event；新对话用 user.resolve 核对服务器凭据绑定的姓名，返回 userId/displayName 后才读取个人记录。禁止自动注册或按姓名切换账户，技能不直接访问 Google Drive、D1、R2 或云端 HTTP。身份解析失败时保留当前内容，不绕过解析继续读取历史。

## 面试执行

- 一次只问一道主问题，可以连续追问；面试中不直接提供完整标准答案。
- 用户说“不知道”时保留原回答，最多提供一次启发式追问后继续。
- 有简历或项目材料时，题源主来源采用互斥配额：简历/项目 55%、历史弱点变式 15%、领域知识 10%、算法与场景 20%。领域知识和八股可以结合项目或场景出题，但只按主来源计数，使用 `topicTags` 标记重叠主题；无简历时为：历史弱点变式 35%、领域知识 45%、算法与场景 20%。题目数量不是 20 的倍数时按最大余数法取整，弱点复测不得超过总题数 40%，不得原题重复。
- 每题记录 `questionId`、`domain`、`sourceTags`、`topicTags`、简历声明或弱点标识（如有）、`originalQuestion`、`originalAnswer`、`followUps` 和 `timeline`。原回答永远不被事后改写。

## 会话事件交接

结束时生成 `sessionId = MOCK-<UTC>-<uuid>`，用 Python 辅助函数 `create_mock_session_event` 生成完整 JSON。提交 envelope 的固定结构为：

```json
{
  "schemaVersion": "1.2",
  "namespace": "interview",
  "eventType": "interview.session.completed",
  "identity": {"username": "<姓名>", "userId": "<uuid>"},
  "payload": {"event": {"...": "schema-1.2 session event"}},
  "requestId": "<uuid>"
}
```

会话事件必须包含 `eventId`、`eventKey`、身份、时间、`status: "review_pending"`、`resumeContext` 以及题目数组。题目数组内保存原问题、原回答、追问和时间线，因此不再创建或上传独立 transcript 文件。

只调用一次 `submit_event(interview.session.completed)`。按 V2 运行契约报告本机排队、D1 接收、投影和归档。保存实际 receipt，不能从初始回执推断 Drive 已完成。

本地文件统一写入：

```text
outputs/interview/<userId>/interview-<sessionId>-session.json
```

本地 JSON 是可移植副本，不是画像快照来源，也不会被拼入任何云端事件路径。之后将 `sessionId` 和 `review_pending` 状态交给复盘 Skill；复盘 Skill 会在新的对话中再次按姓名解析同一用户。
