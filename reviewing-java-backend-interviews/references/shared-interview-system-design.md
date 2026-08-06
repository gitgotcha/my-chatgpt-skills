# 联合面试系统设计

## 目标与边界

两个 Skill 共同实现多候选人、跨轮次的面试闭环。`conducting-java-backend-mock-interviews` 负责身份确认、简历选择、模拟出题和原始问答固化；`reviewing-java-backend-interviews` 是唯一的统一复盘、DOCX 报告和确定性画像更新实现方。真实候选人的资料不进入本仓库；测试只使用虚构数据和临时目录。

系统的唯一候选人主键是 `candidate_id`。每轮先从仅含摘要的候选人索引检索，再向用户展示 ID、姓名和备注并要求二次确认。确认后创建不可变的 `ConfirmedCandidateContext`；所有读写均校验同一 `candidate_id`，不匹配或身份未确认时立即中止。

## 运行时与交接

当前 Codex 运行时没有可验证的 Skill 动态加载/调用接口。因此模拟 Skill 不会伪造复盘、报告或画像更新。它会以版本化 Schema 固化 `MOCK-*` 会话、`raw_transcript.md` 和带候选人锁的交接清单，并置为 `review_pending`。在能够调用 reviewing Skill 的环境中，reviewing 消费该不可变会话，产生统一 Review、报告和画像事件；否则会话保留，明确提示需要继续复盘。

真实面试由 reviewing 直接接收 `REAL-*` 会话。默认生成 Review、报告和待确认的画像变化预览；只有用户确认才应用事件。模拟 Review 的已校验事件自动应用。云端文件能力不可用时，状态为 `cloud_persistence_pending`，且不把本地临时路径称作已持久化。

## 数据协议

两套 Skill 都保存内容相同、以版本号约束的 JSON Schema 和契约清单：CandidateSummary、Candidate、CandidateIndex、ResumeIndex、ResumeMetadata、ResumeClaims、ConfirmedCandidateContext、InterviewSession、QuestionAnswer、Review、CandidateProfile、ProfileUpdateEvent、CorrectionEvent 与 CommitRecoveryState。测试比较共享副本的内容，防止接口漂移。

CandidateProfile 按 `domain_profiles` 隔离技术能力，`general_competencies` 跨领域累计。每题有独立领域、来源标签、简历声明 ID 和复测弱点 ID。简历声明只影响出题，绝不直接变为能力证据。领域解析优先本轮显式选择、材料、历史画像，最后才用 Java 后端；混合且置信度不足时必须要求用户选择。

## 确定性画像更新

reviewing 的 Python 核心提供 `validate_artifact(data, schema_name)`、`apply_review_event(profile, event)` 与 `rebuild_profile(snapshot, active_events, correction)`。它不调用模型；模型输出的仅是 Schema 合法的 Review 和事件草案。事件幂等键为 `candidate_id + session_id + review_version`，更新时验证候选人锁与预期 `profile_version`。冲突会停止并重读重算，禁止覆盖。

每次应用先保留旧快照，在临时状态构建和校验新画像，最后才切换当前画像并标记事件已应用。若切换后的会话状态更新失败，恢复状态支持幂等重试。Review 修正生成 V2 与 CorrectionEvent：从 V1 前快照排除 V1，应用 V2 后按序重放后续有效事件；不重新调用模型，也不丢失后续更新。

## 报告与验证

两类 Review 采用同一逐题评价结构，包含原问题、原回答、正确性/完整性、遗漏与归因、口语化更优回答、完整参考答案、追问关联、优势/薄弱项/建议和画像变化。报告包含候选人姓名与 ID、类型、领域、时间、session ID、Review 版本与画像变化摘要。

本地测试使用临时文件系统替身覆盖身份隔离、首轮默认、简历驱动、领域切换、弱点变式、真实面试确认、幂等、修正重放、故障恢复和下载产物。报告生成后必须渲染为页面图像，检查中文字体、表格、标题、分页和长文本。云端冒烟只在实际 ChatGPT Library 文件能力可用时，使用隔离的 `TEST-*` 候选人执行；否则标记未验证。

## 文件布局

`reviewing` 新增 `schemas/`、`scripts/interview_core.py`、`scripts/storage_protocol.py`、测试 fixtures 与端到端测试；它保有唯一的画像更新逻辑。`conducting` 新增相同的 Schema 副本、会话固化/交接辅助脚本和测试；不复制复盘或画像更新算法。两边的 `SKILL.md` 与协议文件会更新为身份确认、领域/简历决策、状态机、交接和失败处理的可执行指令。

## 非目标

不实现或伪造 ChatGPT Library API；不存储原始音频；不读取、修改或提交真实候选人资料；不把 `D:\\Interviews` 作为运行依赖；不创建第三个共享 Skill。
