# 用户画像与交接契约

身份只由 `submit_event` 按姓名解析得到：Worker 返回规范化的 `username` 与全局 `userId`，本轮所有会话、问题和交接包都使用同一个 `userId`。解析前不能读取简历、画像或会话；同名冲突无法消解时停止并要求人工选择。

读取画像时只取选定领域的 `next_interview_guidance` 与稳定弱点。技术弱点不得跨领域污染；沟通、项目表达和问题分析可以作为通用能力使用。弱点题使用业务场景、对比、代码判断或异常边界等变式，数量不超过总题数 40%。

会话事件由 Worker 追加到 `my-chatGPT-skills/users/<userId>/interview/events/`。结束时只生成 `mock_interview` 原始会话，包含 `MOCK-*` ID、`evidence_type: system_transcript`、`evidence_confidence: 0.6`、逐题元数据、回答、交接目标和 `review_pending`。模拟 Skill 不生成 `evidence_delta`、不创建画像快照、不更新画像。由 reviewing Skill 消费交接后，才依据统一 Review 创建确定性事件。

提交回执为 `deliveryState: "pending"` 时，会话已在本机 SQLite Outbox 持久排队；`cloud_accepted` 时已进入 D1 Outbox，但 Drive 仍异步处理。会话业务状态保持 `review_pending`；不得退回旧目录、直接写 Drive或静默切换用户。
