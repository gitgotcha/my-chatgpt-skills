---
name: conducting-java-backend-mock-interviews
description: Use when conducting a candidate-locked mock technical interview and submitting immutable source evidence through the reliable-drive-sync MCP.
---

# 模拟面试执行与 MCP 交接

本 Skill 只负责候选人确认、逐题模拟、原始证据整理与 MCP 交接；不自行做最终评分、复盘或画像更新。**不得直接读写 Google Drive、D1、R2 或云端 HTTP 接口。**所有持久化只能调用 `reliable-drive-sync` MCP。

## MCP 契约

启动前确认本机 MCP 已配置 `RELIABLE_DRIVE_SYNC_INGRESS_URL` 与 `RELIABLE_DRIVE_SYNC_INGRESS_SHARED_SECRET`。可用工具：

- `list_candidates(query?, limit?)`：只返回候选人摘要。
- `create_candidate(displayName, distinguishingNote?, resume?)`：创建候选人并只返回摘要。
- `get_candidate_context(candidateId, selectedDomain?, resumeId?, sessionId?)`：确认候选人后才可调用。
- `submit_artifact(...)`：把 JSON、Markdown 或 DOCX 直接写入已确认候选人的 Drive 文件夹。

若 MCP 未配置、工具不可用或 Drive 写入返回错误，保留本轮内容在对话中并明确说明“尚未持久化”；立即停止后续持久化逻辑，不要退回到 Drive 连接器或伪称已保存。

## 强制启动顺序

1. 先用 `list_candidates` 搜索或展示摘要。若不存在目标候选人，调用 `create_candidate`；展示返回的候选人 ID、姓名/备注后，仍须明确二次确认。未确认前，不读取候选人上下文、简历、画像或历史会话。
2. 展示候选人 ID、姓名/备注，要求用户明确二次确认。姓名不是主键；同名时必须选择 `candidateId`。
3. 锁定 `ConfirmedCandidateContext`：`candidateId`、`candidateFolderId`、`displayName`、`confirmedByUser: true`、`confirmedAt`、`activeResumeArtifactKey`、`selectedDomain`。本轮任何 MCP 读取或提交都使用此 ID 与文件夹 ID。
4. 仅在锁定后调用 `get_candidate_context`；询问当前简历、是否更换/上传或不使用。简历声明只用于出题，绝不直接变成能力证据。
5. 领域优先级为本轮明确方向、简历、候选人上下文、Java 后端默认；混合材料且无法可靠判断时让用户选择。

## 面试执行

- 一次只问一道主问题，可连续追问；面试中不提供完整标准答案。
- 用户说“不会”时保留原回答，最多一次启发追问后继续。
- 使用简历时题源目标：简历/项目 35%、历史弱点变式 30%、领域知识 25%、算法与场景 10%；不使用简历时为 35%、45%、20%。弱点复测不超过总题数 40%，不得原题重复。
- 每题记录 `questionId`、领域、`sourceTags`、`topicTags`、简历声明 ID、弱点 ID、原问题、原回答、追问和时间线。

## 结束、不可变产物与交接

结束时生成 `sessionId = MOCK-<UTC>-<uuid>`，并以同一个 `candidateId/sessionId` 调用 MCP 依次提交：

1. `session.json`：`artifactType: "session"`，完整锁定上下文、题目索引和状态 `review_pending`。
2. `raw_transcript.md`：`artifactType: "raw_transcript"`，原始问答、追问和时间线，不做事后改写。

每个提交均必须具备：

```json
{
  "schemaVersion": "1",
  "artifactId": "UUID",
  "artifactKey": "<candidateId>:interview:<sessionId>:<artifactType>:v1",
  "candidateId": "...",
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

`submit_artifact` 只有在 Drive 返回文件 ID 后才算成功；任一提交错误时立即停止，不得继续生成或提交后续持久化产物。成功后将 `sessionId`、两项 `artifactKey` 和 `review_pending` 交给 `reviewing-java-backend-interviews`。
