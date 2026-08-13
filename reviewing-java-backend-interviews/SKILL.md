---
name: reviewing-java-backend-interviews
description: Use when reviewing a candidate-locked mock or real interview through the reliable-drive-sync MCP, with immutable evidence and deterministic profile update events.
---

# 统一面试复盘、画像事件与 MCP

本 Skill 是模拟与真实面试的统一复盘方。**不得直接操作 Google Drive、D1、R2、Google API 或云端 HTTP。**候选人读取、会话证据读取和所有产物写入都必须经过 `reliable-drive-sync` MCP；MCP 负责本机 Outbox、云端任务、R2 暂存与最终 Drive 同步。

## MCP 工具与边界

- `list_candidates(query?, limit?)`：确认前只允许读取摘要。
- `create_candidate(displayName, distinguishingNote?, resume?)`：创建候选人并只返回摘要，创建后仍需确认 ID。
- `get_candidate_context(candidateId, selectedDomain?, resumeId?, sessionId?)`：确认后读取候选人上下文与已提交产物索引。
- `read_artifact(candidateId, artifactKey)`：只读取已同步的 JSON/Markdown 产物；DOCX 不读取全文。
- `submit_artifact(...)`：提交 JSON、Markdown、DOCX，不经任何直连云端渠道。
- `submit_event(...)`：提交确定性、可重放的学习/画像事件；不可携带二进制材料。

工具不可用或 Drive 写入错误时如实报告“尚未持久化”，立即停止本次后续持久化动作；绝不使用旧的 Drive 直写兜底。

## 强制启动顺序

1. `list_candidates` 搜索候选人摘要；找不到时可调用 `create_candidate`，展示结果并要求用户确认返回的 `candidateId`。用户确认前禁止读取详细上下文。
2. 锁定包含 `candidateFolderId` 的 `ConfirmedCandidateContext` 并调用 `get_candidate_context`。候选人 ID 不一致、身份不明或用户取消时立即停止。
3. 找到 `MOCK-*` 的 `session.json` 与 `raw_transcript.md`；分别用 `read_artifact` 读取。真实面试由用户提供原始记录后，先作为同一会话的不可变 `session.json` 与 `raw_transcript.md` 提交。
4. 依据真实题目内容确定领域；混合且置信不足时让用户选择。

## 统一复盘要求

逐题保存原问题、候选人原回答、追问关联、正确性/完整性、缺失与错误、失分归因、更好的口语回答、完整参考答案、表达分析和变式复测。Review 中必须有 `sourceType`、`evidenceType`、`evidenceConfidence`；候选人回忆不等同完整转写。

生成以下不可变产物，使用相同的 `candidateId/sessionId`，`artifactKey` 格式为 `<candidateId>:interview:<sessionId>:<artifactType>:v<reviewVersion>`：

1. `review.json`，`artifactType: "review"`，包含逐题分析与版本。
2. `profile_update_event.json`，`artifactType: "profile_update"`，仅包含确定性画像变化、`expectedProfileVersion`、`eventKey`、证据引用与状态。
3. `review_report.docx`，`artifactType: "report"`，必须在提交前渲染检查；报告含候选人姓名/ID、类型、领域、时间、session ID、版本、逐题分析、画像变化和下一轮建议。

每个产物都使用 `submit_artifact`，以原始字节 Base64 和 SHA-256 构成不可变提交。`profile_update` 的 `dependsOn` 必须列出本次 `session`、`raw_transcript` 与 `review` 的 artifact keys；`report` 至少依赖 `review`。

## 确定性画像事件

Python/本地确定性逻辑只负责 Schema 校验、事件应用和快照重放，不重新调用模型。事件键固定为 `candidateId + sessionId + reviewVersion`；技术弱点按领域隔离，通用能力可跨领域累计；同一弱点仅在两个不同会话、不同问法的正确证据后关闭。

模拟复盘的已校验事件可通过 `submit_event` 自动提交。真实复盘默认只提交报告和变化预览，状态 `pending`；只有用户明确确认才提交 `profile_update` 事件。拒绝时保留报告、将变更标记 `rejected`，当前画像不变。修正已应用 Review 时创建 V2/CorrectionEvent，并从 V1 前快照重放，不丢失后续历史。

每次提交只有在 Drive 返回文件 ID 后才可称为已保存；任一错误时停止本次后续写入并保留可重试的内容在对话中。
