---
name: reviewing-java-backend-interviews
description: Use when reviewing a candidate-locked mock or real interview with a unified evidence protocol, report, and deterministic profile update.
---

# 统一面试复盘与能力画像

本 Skill 是模拟与真实面试共用的复盘、报告和确定性画像更新实现方。两类面试的评价标准与 JSON 协议相同，仅证据来源、置信度和应用确认策略不同。

## 强制启动顺序

1. 只读取 CandidateIndex 摘要，按 ID 或姓名搜索并展示 ID、姓名、区分备注；未确认前禁止读取详细画像、简历和会话。
2. 要求用户明确二次确认，创建并锁定 `ConfirmedCandidateContext`。所有读取、报告和更新都校验其 `candidate_id`；任何不一致立即终止，切换候选人必须结束当前会话后重新确认。
3. 读取已锁定的 `MOCK-*` 交接会话或用户提供的 `REAL-*` 记录。先固化原始问答和转写；不保存原始音频。
4. 识别实际领域：真实问题内容优先于 JD、简历和 Java 默认。逐题标记领域；混合材料置信不足时要求用户选择。

## 统一复盘

每题保存原问题、候选人原回答、追问与关联、正确性/完整性、缺失与错误、失分归因、更好的口语回答、完整参考答案、表达分析和变式复测。Review 必须含 `source_type`、`evidence_type` 与 `evidence_confidence`。候选人回忆的可信度不能等同完整转写，事后补充不计现场表现。

生成 `raw_transcript.md`、`review_vN.json`、`profile_update_event_vN.json`（若适用）和 `review_report_vN.docx`。报告必须包含候选人姓名/ID、类型、领域、时间、session ID、版本、逐题分析、画像变化和下一轮建议。生成后实际渲染并检查页面。

## 确定性画像与确认

Python 只做 Schema 校验、确定性事件应用和快照重放；不重新调用模型。事件键为 `candidate_id + session_id + review_version`，以预期 `profile_version` 乐观锁提交。技术弱点按领域隔离，通用能力可跨领域累计；同一弱点只在两场不同会话、不同问法的正确证据后关闭。

模拟复盘的已校验事件自动应用。真实复盘默认先生成报告与变化预览，状态为 `pending`，仅在用户明确确认后应用；拒绝时报告保留、事件标记 `rejected`、当前画像不变。修正已应用的 Review 时创建 V2 与 CorrectionEvent，从 V1 前快照排除旧事件、应用 V2 并重放随后有效事件，禁止丢失后续历史。

本轮正式云端后端为用户授权的 Google Drive；运行细则见 `references/google-drive-runtime.md`。连接器不可用时使用 `cloud_persistence_pending` 或 `review_pending` 如实说明，绝不把本地替身称为云端持久化。真实数据只在云端文件空间保存；测试只使用临时目录和 `TEST-*` 虚构候选人。
