---
name: conducting-java-backend-mock-interviews
description: Use when conducting a Java backend mock interview for a user resolved by display name, with one immutable submit_event handoff.
---

# Java 后端模拟面试

本 Skill 负责设备账户授权、逐题模拟、原始问答证据整理和会话事件交接；不做最终评分、整场复盘或画像更新。它不直接访问 Google Drive、D1、R2 或云端 HTTP。云端持久化只通过 MCP 暴露的唯一工具 `submit_event` 完成。

所有云端数据只写入唯一规范插件根 `DriveRoot/my-chatGPT-skills/`。模拟会话事件由 Worker 追加到 `users/<userId>/interview/events/`；本 Skill 不生成画像快照，也不在会话中更新画像。

## V2 设备账户授权

每次新对话先查询设备绑定状态，不能把姓名或聊天记忆当作凭据：

1. 调用 `submit_event` 的 `account.current`；只有 `state:"authenticated"` 与完整 `bindingContext` 都有效时，才读取历史或开始面试。
2. 个人会话事件携带最近一次上下文；账户切换仅响应用户明确的 `account.switch`/`account.unbind` 请求。
3. 遇到 `binding_changed`、`reauth_required` 或 `verification_unavailable`，停止个人操作并重新查询 current。
4. 新账户使用 `account.register`，秘密和配对码只在安全界面处理。

账户授权失败时，保留当前对话内容，不声称已保存，也不绕过授权继续读取历史。

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

只调用一次 `submit_event(interview.session.completed)`，并携带当前 `bindingContext`。Worker 把事件追加到 `my-chatGPT-skills/users/<userId>/interview/events/`，不创建画像快照。成功回执用于本地副本元数据；云端失败时仍写本地副本，并如实标记待处理，不得伪称云端已保存。

本地文件统一写入：

```text
outputs/interview/<userId>/interview-<sessionId>-session.json
```

本地 JSON 是可移植副本，不是画像快照来源，也不会被拼入任何云端事件路径。之后将 `sessionId` 和 `review_pending` 状态交给复盘 Skill；复盘 Skill 也必须通过 `account.current` 获取上下文。
