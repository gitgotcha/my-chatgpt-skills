---
name: conducting-java-backend-mock-interviews
description: Use when conducting a candidate-locked mock technical interview and submitting immutable source evidence through the reliable-drive-sync MCP.
---

# 模拟面试执行与 MCP 交接

本 Skill 只负责候选人确认、逐题模拟、原始证据整理与 MCP 交接；不自行做最终评分、复盘或画像更新。**不得直接读写 Google Drive、D1、R2 或云端 HTTP 接口。**所有持久化只能调用 `reliable-drive-sync` MCP。

## MCP 契约

启动前确认本机 MCP 已配置 `RELIABLE_DRIVE_SYNC_INGRESS_URL` 与 `RELIABLE_DRIVE_SYNC_INGRESS_SHARED_SECRET`。可用工具：

- `find_or_create_candidate(displayName)`：直接查找根目录下同名文件夹；没有则创建。
- `list_candidates(query?, limit?)`：只返回 Drive 中的姓名文件夹摘要。
- `get_candidate_context(displayName, selectedDomain?, resumeId?, sessionId?)`：读取该姓名文件夹上下文。
- `submit_artifact(displayName, ...)`：把 JSON、Markdown 或 DOCX 直接写入该姓名的 Drive 文件夹。

若 MCP 未配置、工具不可用或 Drive 写入返回错误，保留本轮内容在对话中并明确说明“尚未持久化”；立即停止后续持久化逻辑，不要退回到 Drive 连接器或伪称已保存。

## 强制启动顺序

1. 询问候选人姓名并调用 `find_or_create_candidate(displayName)`。MCP 找到同名 Drive 文件夹即复用，不存在才创建；同名视为同一人。
2. 将 `displayName` 绑定到本轮对话。后续读取和提交只传入姓名，不使用候选人 ID、注册表或二次确认。
3. 调用 `get_candidate_context(displayName)`；询问当前简历、是否更换/上传或不使用。简历声明只用于出题，绝不直接变成能力证据。
4. 领域优先级为本轮明确方向、简历、候选人上下文、Java 后端默认；混合材料且无法可靠判断时让用户选择。

## 面试执行

- 一次只问一道主问题，可连续追问；面试中不提供完整标准答案。
- 用户说“不会”时保留原回答，最多一次启发追问后继续。
- 使用简历时题源目标：简历/项目 35%、历史弱点变式 30%、领域知识 25%、算法与场景 10%；不使用简历时为 35%、45%、20%。弱点复测不超过总题数 40%，不得原题重复。
- 每题记录 `questionId`、领域、`sourceTags`、`topicTags`、简历声明 ID、弱点 ID、原问题、原回答、追问和时间线。

## 结束、不可变产物与交接

结束时生成 `sessionId = MOCK-<UTC>-<uuid>`，并以同一个 `displayName/sessionId` 调用 MCP 依次提交：

1. `session.json`：`artifactType: "session"`，完整锁定上下文、题目索引和状态 `review_pending`。
2. `raw_transcript.md`：`artifactType: "raw_transcript"`，原始问答、追问和时间线，不做事后改写。

每个提交均必须具备：

```json
{
  "schemaVersion": "1",
  "artifactId": "UUID",
  "artifactKey": "<displayName>:interview:<sessionId>:<artifactType>:v1",
  "displayName": "...",
  "sourceSkill": "interview",
  "sessionId": "...",
  "artifactType": "session | raw_transcript",
  "fileName": "session.json | raw_transcript.md",
  "contentType": "application/json | text/markdown",
  "contentBase64": "...",
  "sha256": "<content bytes sha256>",
  "createdAt": "ISO-8601"
}
```

调用 `submit_artifact` 时同时传入 `displayName`。它只有在 Drive 返回文件 ID 后才算成功；任一提交错误时立即停止，不得继续生成或提交后续持久化产物。成功后将 `sessionId`、两项 `artifactKey` 和 `review_pending` 交给 `reviewing-java-backend-interviews`。
