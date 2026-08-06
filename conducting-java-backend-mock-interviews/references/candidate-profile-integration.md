# 候选人画像与交接契约

先用 CandidateIndex 摘要定位候选人，再通过 ID、姓名和区分备注获得用户二次确认。确认前不能读取简历、画像或会话。确认后锁定 `ConfirmedCandidateContext`；本轮所有会话、问题和交接包使用同一 `candidate_id`。

读取画像时只取选定领域的 `next_interview_guidance` 与稳定弱点。技术弱点不得跨领域污染；沟通、项目表达和问题分析可以作为通用能力使用。弱点题使用业务场景、对比、代码判断或异常边界等变式，数量不超过总题数 40%。

结束时只生成 `mock_interview` 原始会话，包含 `MOCK-*` ID、`evidence_type: system_transcript`、`evidence_confidence: 0.6`、逐题元数据、回答、交接目标和 `review_pending`。模拟 Skill 不生成 `evidence_delta`、不更新画像。由 reviewing Skill 消费交接包后，才依据统一 Review 创建确定性事件。

云端不可用时会话保留为 `cloud_persistence_pending` 或 `review_pending`；不得退回到本机硬编码目录，也不得静默切换候选人。
