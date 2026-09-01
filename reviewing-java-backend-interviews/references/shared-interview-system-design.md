# 联合面试系统设计

## 目标与边界

两个 Skill 共同实现按姓名解析的多轮面试闭环。`conducting-java-backend-mock-interviews` 负责按姓名解析、模拟出题和原始问答固化；`reviewing-java-backend-interviews` 是唯一的统一复盘、本地 DOCX 报告和确定性画像事件生成方。真实用户资料不进入本仓库；测试只使用虚构数据和临时目录。

系统的唯一主键是全局 `userId`，由 `submit_event` 按姓名解析或创建。旧的候选人索引、候选人目录与候选人锁已废弃，也不再要求二次确认候选人身份。同名冲突无法消解时停止并要求人工选择，不自动合并。

## 运行时与交接

两个 Skill 都不直接调用 Google Drive。它们只构造 schema-1.2 事件并调用唯一暴露的 `submit_event`；Worker 负责校验、解析用户、追加事件和物化快照。

模拟 Skill 固化 `MOCK-*` 会话事件并置为 `review_pending`，会话内不生成画像快照。reviewing 消费该不可变会话，产生统一 Review、本地报告和画像变化事件。真实面试由 reviewing 直接接收 `REAL-*` 会话：默认生成 Review、报告和待确认的画像变化预览，只有用户确认才应用事件；模拟 Review 的已校验事件自动应用。

云端不可用时状态为 `cloud_persistence_pending`，快照失败为 `profile_cache_pending`，且不把本地临时路径称作已持久化。

## 数据协议

两套 Skill 保存字节一致的 `schemas/contracts.schema.json` 与 `manifest.json`，只列出当前 schema-1.2 定义：

```text
Identity, Registration, Question, SessionEvent,
QuestionReview, ProfileChange, ReviewEvent, ProfileSnapshot
```

测试比较共享副本的字节内容，防止接口漂移。每题有独立领域、来源标签和复测弱点 ID。简历声明只影响出题，绝不直接变为能力证据。领域解析优先本轮显式选择、材料、历史画像，最后才用 Java 后端；混合且置信度不足时必须要求用户选择。

## 确定性画像更新

画像 reducer 的唯一活动实现是 Reliable Drive Sync Worker 的 `services/reliable-drive-sync-worker/src/profile-model.js`。Python 核心不再提供 `validate_artifact`、`apply_review_event` 或 `rebuild_profile`。它只构造并校验 schema-1.2 事件、写本地报告副本，并提供与云端无关的领域解析与题源规划纯函数。

Worker 只使用已验证且 `applyProfileChanges === true` 的复盘事件，按 `sessionId` 取最大 `reviewVersion`，生成不可变快照。事件已存在而快照缺失时，同一幂等键重试只补做投影。

## 报告与验证

两类 Review 采用同一逐题评价结构，包含原问题、原回答、正确性/完整性、遗漏与归因、口语化更优回答、完整参考答案、追问关联、优势/薄弱项/建议和画像变化。报告包含姓名、`userId`、类型、领域、时间、`sessionId`、复盘版本与画像变化摘要。

本地测试使用临时目录覆盖姓名解析、按用户隔离、schema 校验、本地副本路径、报告渲染与旧结构拒绝。报告生成后必须渲染为页面图像，检查中文字体、表格、标题、分页和长文本。云端冒烟只在实际 Drive 连接器可用且用户确认根目录时，使用隔离的虚构用户执行；否则标记未验证。

## 文件布局

```text
DriveRoot/my-chatGPT-skills/users/<userId>/interview/events/
DriveRoot/my-chatGPT-skills/users/<userId>/interview/profile/snapshots/
outputs/interview/<userId>/interview-<sessionId>-report.json
outputs/interview/<userId>/interview-<sessionId>-report.docx
```

`reviewing` 保有 `schemas/`、`scripts/interview_core.py`、`scripts/create_review_report.py` 与测试；`conducting` 保有相同的 Schema 副本、会话固化/交接辅助脚本和测试；不复制复盘或画像更新算法。两边的 `SKILL.md` 与协议文件统一描述按姓名解析、领域/简历决策、状态机、交接和失败处理。

## 非目标

不直接调用 Drive API；不存储原始音频；不读取、修改或提交真实用户资料；不把 `D:\Interviews` 作为运行依赖；不创建第三个共享 Skill；不把本地报告作为画像输入或上传云端。
