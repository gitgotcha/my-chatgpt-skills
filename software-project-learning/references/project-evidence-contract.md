# 历史文件：项目问答与证据合同（project contract v1）

> **停用说明（2026-10-27，2026-10-28 更新）：** 本文档属于原 RDS-V2 事件型会话设计，不适用于当前 RDS-JBryon 项目快照。当前项目学习和模拟面试改用 [`rds-jbryon-runtime.md`](rds-jbryon-runtime.md)，不再依赖 UUID project binding、`submit_event` 或 profile/interview event。模拟面试与复盘的内容对象现为 snapshot/2，本文提及的 `create_review_event` 已退役。保留本文仅为旧设计与迁移审计，不得照文执行。

本文件是 `software-project-learning` **唯一的正式项目问答合同来源**。`references/profile-contract.md` 只规定教学提纲画像并链接本文件；`reviewing-java-backend-interviews` 按其自身规则提交评价，本 Skill 只准备交接，不复制其规则。所有构造器在 `scripts/project_evidence.py`，均为纯构造：不生成 ID、不发 HTTP、不写快照。

## 0. 运行前提

- 用户用 `project-12306` 这类可读入口指定项目时，先按[项目别名与入口合同](project-alias-contract.md)解析到稳定 `projectId`，再进入本合同的读取与写入。别名只是选择键：不写进 session/question DTO，不充当 domain、namespace、Drive 路径或 Skill 文件夹；正式事件只用解析出的 UUID 与 basis。解析状态为 unresolved/conflict 时停止依赖历史或快照的操作，普通教学可继续。
- 唯一远端工具：`submit_event`。外层业务 envelope 保持 `schemaVersion:"1.2"`；项目扩展事件在事件对象顶层增加 `projectContractVersion:1`。
- 身份必须由 `user.resolve` 核对；姓名只用于一致性核对，不能替代服务端凭据。
- 所有时间使用带时区偏移的 ISO-8601；回顾日期按 `Asia/Shanghai` 自然日计算。
- 本 Skill 不直接访问 Drive、D1、R2 或 HTTP，也不构造存储路径。

## 1. 能力握手与项目快照查询

共享的 [RDS V2 运行契约](rds-v2-runtime.md) 由多个技能逐字节共用，不能只为某一个技能追加项目参数；因此**项目专属**的 feature 握手、查询参数矩阵与缺 feature 降级规则记录在本文件，通用身份、分页与回执规则仍以共享文件为准。

先读 capabilities：

```json
{"storageVersion":2,"operation":"capabilities","params":{}}
```

只有返回 `storageVersion:2` 且显式声明以下 feature 时，才允许发送项目扩展字段或按项目查询：

```json
{"features":{"interviewProjectSnapshots":{"version":1,"projectFilter":true}}}
```

**缺 feature 时**：继续普通教学；不发送 `projectContractVersion`、`projectEvidence` 等新字段；只保留本地待交接记录（session/review 原文与各自回执），不上云、不建“云端待依赖队列”、不假装已保存。feature 之后重新可用时，用**原 ID、原内容**重试。

项目快照查询沿用 `projection.read`，`namespace=interview`、`projectionName=interview`：

| projectId | rowKind | 行为 |
|---|---|---|
| 有 | 省略 | 返回该项目的三类行，`summary` 为该项目的 `project_summary`（无则 `null`） |
| 有 | `project_summary` / `project_attempt` / `project_weakness` | 只返回该项目该 kind |
| 有 | 其它（含 legacy kind） | `invalid_params` |
| 无 | `project_summary` | 返回当前用户的项目目录（仅摘要元数据），`summary=null` |
| 无 | `project_attempt` / `project_weakness` | `invalid_params` |
| 无 | 省略或 legacy kind | 旧行为：只返回 legacy rowKind，`summary` 为全局 summary |

约束：

- `projectId` 必须是 UUID，且只在 `interview/interview` 下允许；过滤必须发生在服务端 SQL 内，不先取全量再筛。
- `limit≤50`；`summary` 必须受项目范围限制，不得带出其它项目或全局内容；响应 ≤256 KiB。
- cursor 绑定 `user + operation + namespace + projectionName + projectId + rowKind + revision + lastSortTuple`；任一变化返回 `cursor_scope_mismatch`。跨页保持同一 revision；`cursor_expired` / `projection_changed` 从头重读。
- `building=true` 表示构建未完成，不是空快照；`projection_not_found` 表示尚无画像，不是“没学过”或零分。
- `interview.session.list` 默认只列 `mock`/`real`；项目学习会话通过 `project_attempt` 定位。`interview.session.load` 传入 `LEARN-` ID 时必须与协议、路由一起支持，并始终按凭据用户隔离。

## 2. Session 扩展（项目学习）

| 字段 | 约束 |
|---|---|
| `interviewType` | `project_learning` |
| `sessionId` | `LEARN-<UTC compact>-<uuid>`，示例 `LEARN-20261023T020000Z-<uuid>` |
| `projectContractVersion` | `1` |
| `questions[].projectEvidence` | 项目学习 session 中**每题必填** |
| `profileChanges` | 项目学习不得产生全局画像变更；session 不携带该字段，对应 review 的 `profileChanges` 必须为 `[]` |

`originalAnswer` 是首次实际回答；提示后的补答追加进 `timeline`/`followUps`，**不替换首答**。只提出题目、用户尚未回答时不得构造 session；用户说“不会”是有效回答，可以记录。

构造入口：

```python
build_learning_session(identity, questions, *,
                       session_id, event_id, started_at, completed_at)
```

它会调用复盘 Skill 的 `validate_project_session_event` 复核 LEARN 前缀、项目证据、单项目约束与 48/24 KiB 容量；构造器本身不生成任何 ID。

## 3. `questions[].projectEvidence`

| 字段 | 类型与约束 |
|---|---|
| `project` | `projectId`(UUID)、`displayName`(非空)、`basis{kind∈resume_claim\|user_confirmed\|source_learning, key}`、`resumeVersion`(string\|null)、`resumeClaimIds`(string[])、`sourceRevision`(string\|null) |
| `attemptId` | UUID；一次真实独立作答一个 ID |
| `questionKey` | 稳定考点 ID，1–128 字符 `[A-Za-z0-9._-]` |
| `variantId` | 稳定语义变式 ID，≤128 字符 |
| `variantAxes` | 1–4 个非空串，声明改变了什么条件 |
| `purpose` | `initial_assessment` 或 `targeted_retest`；**没有可落库的 `daily_recap` 分支** |
| `sourceSkill` | 本 Skill 固定 `software-project-learning` |
| `provenance` | 见下表 |
| `sourceRefs` | 1–20 个非空串：题目来源目录 ID、源码定位或官方文档 URL；不含私密简历全文 |

### 3.1 provenance

| 字段 | 允许值 | 说明 |
|---|---|---|
| `answerOrigin` | `actual_user` / `user_recall` | `assistant`、`synthetic` 被合同拒绝，不能伪装成用户作答 |
| `assistance` | `none` / `hint` / `answer_shown` | 提示或展示答案都要如实标记 |
| `exactAnswerSeenBefore` | boolean | 作答前是否已看过本题的完整答案 |
| `exposureGroupId` | 非空串，≤128 字符 | 同一次曝光/练习窗口的稳定分组 |

### 3.2 attempt 规则

- 一个 `attemptId` 对应一次真实独立作答；同题的提示与补答仍属该 ID，补答不新建 attempt、不创建“第二次独立通过”。
- 新题、改变条件后的专项复测都是**新 attempt**；后续窗口重新出题时新建 session，旧 session 与旧回答永不覆盖。
- `attemptId` 不能跨 session、question 或 project 复用；服务端以 `attempt_identity_conflict` 拒绝复用，不覆盖原行。
- `variantId` 表示语义变式：换人名、换数字、换项目显示名不算新变式；改变故障模型、约束或时序条件才算。
- 一次性作答、同日多次真实作答都各自保留，不做“每日首答”去重。

## 4. Review 交接

本 Skill 不提交评价。正式评价由 `reviewing-java-backend-interviews` 按同一 rubric 产出并提交；本 Skill 只调用：

```python
prepare_review_handoff(session, assessments, *,
                       review_event_id, review_version, completed_at,
                       recommendations=None)
```

它内部复用 `reviewing-java-backend-interviews/scripts/interview_core.py` 的 `create_review_event`，不复制评分、证据定位或版本规则。`assessments` 的每一项是已填好的 `questionReview`：`questionId`、`assessment`、`evidence`、`recommendations` 与必填的 `projectAssessment`；本 Skill 固定传 `profile_changes=[]`、`apply_profile_changes=true`。返回的是待交接的 `interview.review.completed` 事件，**不发请求**。

| review 字段 | 约束 |
|---|---|
| `sourceSessionEventId` | 必须是已接纳 session 的 `eventId`；session 不存在时先返回 409，不接纳 |
| `reviewVersion` | 正整数；更高有效版本替换旧贡献 |
| `interviewType` | `project_learning`；`profileChanges` 必须为 `[]` |
| `applyProfileChanges` | 项目学习评价固定显式布尔；生效评价为 `true`，仅存档为 `false` |
| `questionReviews[].projectAssessment` | 每题一份，`attemptId` 必须属于该 session 的某道题 |

`projectAssessment` 固定 `rubricVersion:"project-campus-v1"`：

| 项 | 约束 |
|---|---|
| `scores` | `{technical≤30, projectEvidence≤25, causal≤20, tradeoff≤15, expression≤10}` 或 `null` |
| `total` | 五项之和或 `null` |
| `outcome` | `passed` / `partial` / `failed` / `unscored` |
| `evidenceRefs` | `<questionId>:originalAnswer` 或 `<questionId>:timeline:<messageId>`，必须指向该 session 真实存在的内容 |
| `reason` | 非空说明 |
| `weaknesses` | `[{weaknessId,title,outcome∈failed\|passed\|observed}]` |

训练口径通过门槛（不是公司录用线）：`total≥80`、`technical≥24`、`projectEvidence≥18`、`causal≥14`，且无颠倒库存/事务/超时结果等关键错误。证据不足时 `scores=null`、`total=null`、`outcome=unscored`。纯八股或算法题沿用原 rubric，不塞入本对象。

评价撤回：提交更高 `reviewVersion` 的 `unscored` 且 `weaknesses=[]`，服务端从空状态重建该代，不残留旧计数；`applyProfileChanges=false` 只存档，不撤销已生效版本。新复测必须新建 attempt/session，不能靠提升 reviewVersion 冒充。

## 5. 回顾零写入

次日开场回顾只读：读取 `profile/backend-project-learning` 的 `learning-outline`，按 `observedAt` 在 `Asia/Shanghai` 自然日定位“昨天”，用用户口述补全框架。

- 判定标准是**业务写入次数为 0、新增 attempt 为 0、新增 review 为 0、新增 outline 为 0**，不是“回顾不计分”。
- 回顾的提问、回答、提示、评价只存在于当轮上下文；不得通过 outline、附件、报告、`profileChanges` 或任何旁路保存。
- 回顾里确认或提到 `project-12306` 也不写 project-binding；确需配置别名，等回顾明确结束后单独确认，避免把回顾中的一句话当成跨会话授权。
- 回顾问答不得改名为正式题后补录；回顾回答再精彩也不能成为 attempt。
- 用户随后要求专项复测时，必须重新出题、新建 attempt 与 session，不复用回顾对话。
- `projection_not_found`、`building=true`、读取失败都表示历史未知，不能解释为“没学过”或零分；无昨日记录时如实说明无可靠记录。
- 构造门控：`classify_turn(context)` 把回顾优先判为 `recap`；`plan_turn_writes` 对 recap 恒返回 `{"session": False, "outline": False, "assessment": False}`。只有 `teaching` 且实际讲过时才允许构造教学提纲，只有 `formal_qa` 且用户实际作答时才允许构造 session。

## 6. 独立通过与弱点关闭（服务端定义）

服务端计算，忽略客户端任何“已关闭”声称。排序键：`(session.completedAt 的 UTC 毫秒, sessionId, question 在数组中的整数 index, attemptId)`；使用规范 UTC 与补零 index，禁止不同时区原始字符串或未补零数字做字典序。

一次 attempt 记 `eligibleIndependentPass`，当且仅当同时满足：

```text
assessment.outcome == passed
provenance.answerOrigin == actual_user
provenance.assistance == none
provenance.exactAnswerSeenBefore == false
```

在最近一次有效 failed 之后统计：

- 1 个合格通过 → `improving`；
- ≥2 个不同 session、≥2 个不同 `variantId`、≥2 个不同 `exposureGroupId` 的合格通过 → `closed`；
- 出现新的有效 failed → 回到 `open` 并开启新周期（旧通过不计入新周期）。

提示、看过答案、`user_recall` 都不算独立通过。同日多次真实作答各自保留。本 Skill 不自行判定弱点是否关闭；它只如实记录作答与辅助程度。

## 7. 容量与稳定拒绝码

| 对象 | 上限 | 超限处理 |
|---|---|---|
| 整份 envelope canonical bytes | 48 KiB | 拒绝，保留本地原文，提示拆分或缩短 |
| 单题原始记录（题目+原答+timeline） | 24 KiB | 同上 |
| 单题 `projectAssessment` | 8 KiB | 同上 |

不截断、不静默丢弃。稳定码包括：`project_contract_version_unsupported`、`invalid_project_evidence`、`project_identity_conflict`、`attempt_identity_conflict`、`source_session_not_committed`、`review_source_mismatch`、`assessment_question_mismatch`、`assessment_score_invalid`、`assessment_evidence_unresolvable`、`project_envelope_too_large`。

## 8. 交接、回执与恢复

- 学习 session 与 review 不承诺跨请求原子性：session 已入库而 review 未到时，只显示“待评估”。
- 本地交接清单保存两份原 envelope 及各自回执；重试保持 `requestId`/`eventId`/`eventKey` 与内容不变。
- review 先到：接纳前返回 409，不建投影任务；Outbox 按退避重试，连续 5 次仍缺依赖转 `blocked` 并保留原文；之后用同一 envelope 重试时，桥接层只读确认 session 已提交，再把原记录恢复 `pending`。永久错误不走该恢复。
- 恢复不改变任何 ID，不新建云端“待依赖队列”。
- 回执分阶段，不把前级当后级：`pending`（本机排队）、`d1_committed`（D1 接纳）、`projected`（读视图已应用）、`archived`（Drive 归档完成）。用首次提交的 `requestId` 或 `eventId` 查询，不构造轮询事件。

## 9. 事件骨架（占位）

下面是结构示意，**省略了必填字段，不能直接提交**；所有 ID、时间和内容都必须替换为当次真实值。

session：

```json
{
  "schemaVersion": "1.2",
  "eventType": "interview.session.completed",
  "sessionId": "LEARN-<UTC compact>-<uuid>",
  "interviewType": "project_learning",
  "projectContractVersion": 1,
  "status": "review_pending",
  "questions": [
    {
      "questionId": "<questionId>",
      "originalAnswer": "<首次实际作答>",
      "timeline": [{"messageId": "<messageId>", "role": "user"}],
      "projectEvidence": {
        "attemptId": "<uuid>",
        "purpose": "initial_assessment",
        "sourceSkill": "software-project-learning",
        "provenance": {
          "answerOrigin": "actual_user",
          "assistance": "none",
          "exactAnswerSeenBefore": false,
          "exposureGroupId": "<exposureGroupId>"
        }
      }
    }
  ]
}
```

review 骨架由 `prepare_review_handoff` 生成：`eventType:"interview.review.completed"`、`sourceSessionEventId`、`reviewVersion`、`profileChanges:[]`、`questionReviews[].projectAssessment`。所有 ID、时间和内容都必须替换为当次真实值。
