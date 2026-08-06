# 模拟会话交接与报告边界

模拟 Skill 只产生可复盘材料：候选人锁、简历锁、`MOCK-*` 会话、逐题问答、`raw_transcript.md` 和交接校验摘要。未复盘会话状态为 `review_pending`，`create_interview_report.py` 必须拒绝它，避免把未验证的材料当成最终报告。

reviewing Skill 处理交接后使用统一 Review 生成报告。最终报告固定包含候选人姓名与 ID、面试类型、主要领域、时间、session ID、Review 版本、逐题分析、参考答案、总体评价、画像变化摘要和下一轮建议。DOCX 必须渲染后逐页检查；无法调用 reviewing 时必须说明并保留待处理状态。
