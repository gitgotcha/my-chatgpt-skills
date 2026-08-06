# 共享画像协议

协议版本为 `1.0`，Schema 位于 `schemas/contracts.schema.json`。候选人 ID 是唯一主键；CandidateIndex 仅提供摘要，详情只能在 `ConfirmedCandidateContext` 二次确认后读取。真实候选人数据由运行时 Google Drive 连接器保存；Python 不实现或伪造云端 API。

CandidateProfile 必含 `schema_version`、`candidate_id`、`profile_version`、`head_event_id`、`domain_profiles`、`general_competencies` 和事件应用键。每个领域的技术弱点带稳定 ID、状态、证据会话 ID 和变式记录；通用能力可跨领域累计。简历声明不得直接构成能力证据。

ProfileUpdateEvent 的幂等键为 `candidate_id + session_id + review_version`，必须校验候选人锁与 `expected_profile_version`。先保存旧快照，在临时状态构建和校验新画像，最后切换 current profile；冲突或写入失败时停止提交并保留可重试恢复状态。模拟事件自动应用，真实事件只有用户确认后应用。

Review 修正采用快照和事件重放：保留 V1，创建 V2 与 CorrectionEvent，从 V1 前快照排除旧事件、应用 V2、顺序重放其后的有效事件，并用乐观锁切换当前画像。不得恢复到旧快照后停止，也不得重新调用模型复盘后续历史。
