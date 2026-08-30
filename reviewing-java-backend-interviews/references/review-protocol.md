# 统一复盘协议

模拟和真实会话均使用同一 schema-1.2 Review 结构。区别只在 `interviewType`（`mock` 或 `real`）、`evidenceType`（`full_transcript`、`partial_transcript`、`user_recall`、`structured_notes`、`live_notes`）及 `evidenceConfidence`（`high`、`medium`、`low`）。低可信回忆不能与完整转写等权；清洗转写时只删除无意义口头语，歧义必须标记。

逐题记录 `questionId`、考察意图、正确性、完整性、遗漏、错误、失分归因、更优口语回答、完整参考答案、表达分析和变式复测。逐题领域以实际问题内容为准；真实面试的算法问题按算法标准复盘，即使简历是 Java 后端。

## 复盘顺序

1. 按姓名解析用户，取得 `{userId, username}` 绑定。
2. 读取目标会话与已有复盘版本，构造唯一 `interview.review.completed` 事件。
3. 只调用一次 `submit_event`；Worker 追加事件到 `users/<userId>/interview/events/`。
4. Worker 物化快照到 `users/<userId>/interview/profile/snapshots/`；本 Skill 不创建快照。
5. 生成本地 JSON 与 DOCX 报告并做渲染检查。

模拟 Review 自动应用画像变化；真实 Review 默认生成待确认的预览，用户确认后应用，拒绝后保持 `rejected` 且不改变画像。云端不可用时标记 `cloud_persistence_pending`，快照失败标记 `profile_cache_pending`，明确阻断，不得将本地临时文件冒充云端资料。

## 修正与版本

修正产生新的不可变 `reviewVersion`，不覆盖旧版本。Worker 重建时按 `sessionId` 只取最大 `reviewVersion`，因此历史修正自动生效，无需重放事件或切换当前画像。
