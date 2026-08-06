---
name: conducting-java-backend-mock-interviews
description: Use when conducting a candidate-locked mock technical interview, preserving source evidence and safely handing it to the unified review workflow.
---

# 模拟面试执行与复盘交接

本 Skill 只负责候选人确认、简历选择、逐题模拟、原始证据固化和安全交接；不自行评分、生成最终复盘或更新共享画像。统一复盘和画像更新仅由 `reviewing-java-backend-interviews` 执行。

## 强制启动顺序

1. 只读取 CandidateIndex 的候选人摘要；默认展示最近候选人，支持按姓名或 `candidate_id` 搜索。未确认前禁止读取简历全文、详细画像、会话或候选人文件。
2. 展示候选人 ID、姓名、区分备注，要求用户明确二次确认。姓名不是主键；同名候选人必须选择 ID。
3. 创建并锁定 `ConfirmedCandidateContext`：`candidate_id`、`display_name`、`confirmed_by_user: true`、`confirmed_at`、`active_resume_id`、`selected_domain`。本轮所有读写必须携带该 ID；不匹配、取消或身份不明确时立即停止。
4. 显示当前简历版本，询问使用当前版本、更换、上传或不使用。将选定 `resume_id` 锁定到会话。简历声明只影响出题，绝不直接写成能力证据。
5. 领域优先级为本轮明确方向、简历、该候选人的领域画像、Java 后端默认。简历明显混合且无法可靠选择主领域时，要求用户选择；不得强套 Java 后端。

## 面试执行

- 一次只问一道主问题，可根据回答连续追问；面试中不提供完整标准答案。
- 用户说“不会”时保留原回答，最多一次启发追问，随后继续，避免反复逼问。
- 使用简历时目标题源为：简历/项目 35%、历史弱点变式 30%、领域知识 25%、算法与场景 10%；不使用简历时为 35%、45%、20%。取整可调整，但弱点复测不超过总题数 40%，且不得原题重复。
- 每题记录 `question_id`、领域、`source_tags`、`topic_tags`、简历声明 ID、弱点 ID、原问题、原回答与重要追问。项目覆盖事实、原理、异常和方案比较。
- 无简历无画像时执行首次 Java 后端模拟；实际材料为大模型、算法等领域时按材料组织问题。

## 结束与交接

用户说“结束面试”或达到约定题量后，立即固化 `MOCK-*` 原始会话、`raw_transcript.md` 和带 SHA-256 的交接包。会话状态为 `review_pending`。如果运行环境能够明确继续调用 reviewing Skill，则它消费该不可变会话，按统一标准生成 Review、报告和事件；无法调用时必须说明限制，保留 `review_pending`，不得编造简化评分或污染画像。

本轮正式云端后端为用户授权的 Google Drive；按 reviewing Skill 的 `references/google-drive-runtime.md` 写入候选人锁定范围内的会话交接包。连接器不可用时标记 `cloud_persistence_pending`，保留已固化原始会话并明确受阻点；不得将临时路径称为云端保存成功。`D:\\Interviews` 只能是用户手动下载后的备份，绝不作为运行依赖。
