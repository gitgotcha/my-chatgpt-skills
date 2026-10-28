# 历史文件：画像契约（backend-project-learning / RDS V2）

> **停用说明（2026-10-27）：** 本文定义旧 RDS-V2 profile 画像与 UUID binding，不是当前项目学习/模拟面试的存储规则。RDS-JBryon 项目快照流程见 [`rds-jbryon-runtime.md`](rds-jbryon-runtime.md)。

本文件只描述本 Skill 的两个**中性观察维度**：教学提纲与项目别名绑定。RDS V2 的身份、查询、写入与回执协议见 [RDS V2 运行契约](rds-v2-runtime.md)；正式项目问答、attempt、评价与回顾零写入见 [项目问答与证据合同](project-evidence-contract.md)；别名语法、完整读取预算、解析状态机与冲突处理见 [项目别名与入口合同](project-alias-contract.md)。本文件不重复问答合同或别名解析规则，也不定义第二套规则。

## 1. 域与来源

| 项 | 值 |
|---|---|
| namespace | `profile` |
| domain | `backend-project-learning` |
| sourceSkill | `software-project-learning` |
| 读取入口 | `projection.read`，`projectionName` 为 `backend-project-learning` |
| 写入入口 | `profile.evidence.recorded` |
| 维度 | `learning-outline`、`project-binding` |

`backend-project-learning` 继续沿用，以保持技能改名后的历史连续性。它不是 `algorithm`、`interview`、`resume-knowledge` 或 `planning-execution` 的替代品；正式项目作答写入 `interview` 域的 `interview.session.completed`，评价由复盘 Skill 写入 `interview.review.completed`。

别名是可读的**选择键**，不是权限边界、namespace、Drive 路径或 Skill 文件夹名。鉴权始终由服务器凭据绑定用户；跨项目隔离依赖稳定 `projectId`。正式作答、快照与评价只用解析出的 `projectId` 与 `basis`，不在 session/question DTO 里增加别名字段。

## 2. 两个中性维度与 subjectKey

| dimensionKey | 保存内容 | subjectKey 约定 |
|---|---|---|
| `learning-outline` | 教练**实际讲授过**的中性课程提纲：入口、角色、调用顺序、状态变化、一个必要边界 | `<projectId>:<unitId>`，两段都必须是稳定标识 |
| `project-binding` | 用户**明确确认**的中性别名映射：这个可读别名属于哪个稳定项目 UUID、依据是什么 | 别名本身，例如 `project-12306`；语法与拒绝清单见 [项目别名与入口合同](project-alias-contract.md) |

`projectId` 是项目 UUID（不从别名、路径、显示名或 commit 推导）；`unitId` 是稳定的教学单元键（如 `unit-query-margin`），不是文件路径、显示名或时间戳。subjectKey 不是存储路径，别名也不是。

两个维度都不是成绩：`learning-outline` 只证明“这一节被讲过”，`project-binding` 只证明“这个别名被确认过”。二者都不能推出“已掌握”“答得好”或“面试通过”；项目学习 Skill 不写分数、弱点状态或掌握度结论。

## 3. 记录条件

两个维度各自有记录条件，不能互相套用。**绑定确认不要求讲授消息定位**；提纲也不能因为用户确认过别名而获得“已掌握”的含义。

### 3.1 learning-outline

只有同时满足以下条件才允许构造提纲事件：

- 教练已经在当前对话中**实际讲完**一个可识别的项目单元；
- 能定位到当次讲授消息，形成 `sourceRef=learning-unit:<unitId>:<conversationId>:<teachingMessageId>`；
- 提纲只复述已讲框架，不加入用户表现；
- evidence 为 8—800 字；
- 身份已由 `user.resolve` 核对，写入通过唯一工具 `submit_event`。

记录发生在“讲授完成”之后，而不是用户答完题之后。用户没有回答，不构成跳过教学提纲的理由；用户回答过，也不使提纲升级为能力证据。

### 3.2 project-binding

只有同时满足以下条件才允许构造绑定事件：

- **用户明确确认**“此别名属于这个项目 UUID，依据是 `resume_claim`、`user_confirmed`、`source_learning` 之一”。模型自己猜、从简历项目名/路径/显示名/commit 推导、或仅凭相似名称归属都不算确认；
- 确认消息可定位，形成 `sourceRef=project-confirmation:<conversationId>:<messageId>`。这条定位是**确认消息**，不要求、也不接受用讲授消息代替；
- evidence 是严格 JSON 文本，UTF-8 不超过 2048 字节，解析后正好五个字段（见 §5）；
- `projectAlias` 必须等于 observation 的 `subjectKey`；
- 该别名当前没有活跃绑定，或已有活跃绑定的五字段与本次**完全相同**（相同事实的重复确认是合法的）。一个别名两个 UUID、一个 UUID 两个活跃别名、basis 不一致都算冲突，处理方式见 [项目别名与入口合同](project-alias-contract.md)；
- 写入后，该 `eventKey` 必须能在该 revision 的活跃 `evidenceRefs` 中定位，才启动依赖别名的正式读写。`pending` 只表示本机排队，`d1_committed` 只表示 D1 接纳，都不等于已投影，也不算“已保存”。

上面是**事件内容**的条件；**什么时候允许写**由 [项目别名与入口合同](project-alias-contract.md) 的写入门禁决定：显式配置阶段、有可定位确认，且别名已 `resolved` 或满足首次引导例外。回顾阶段即使满足内容条件也不得写入。

### 3.3 两条共同条件

- 身份必须已核对；不注册、不切换账户，不冒用其他用户；
- 不记录次日回顾的任何内容（见 §6）。

## 4. outcome 与 confidence

协议允许九个 outcome，但本 Skill 的两个维度**只发 `observed`**，不发 `consulted`、`completed`、`correct`、`passed`、`failed` 等任何其它值。

| 字段 | 固定值 | learning-outline 含义 | project-binding 含义 |
|---|---|---|---|
| `outcome` | `observed` | 只证明“这一节被讲过” | 只证明“这个别名被确认过” |
| `confidence` | `high` | 只表示讲授事实可定位 | 只表示确认事实可定位 |

`confidence=high` 不是对用户能力的把握，也不是服务端对映射唯一性的保证：别名没有服务端原子唯一索引，并发确认仍可能产生冲突。

## 5. 五字段绑定证据

绑定 observation 的 `evidence` 是 UTF-8 JSON 文本，最多 2048 字节，解析后**严格只有**下列五个字段。下面是合成结构示例，UUID 与 `basis.key` 都是占位值，不能原样提交。

```json
{
  "bindingVersion": 1,
  "projectAlias": "project-12306",
  "projectId": "00000000-0000-4000-8000-000000000000",
  "displayName": "12306",
  "basis": {
    "kind": "source_learning",
    "key": "confirmed-source:train-12306"
  }
}
```

| 字段 | 约束 |
|---|---|
| `bindingVersion` | 整数常量 `1` |
| `projectAlias` | 必须等于 observation 的 `subjectKey`，语法见 [项目别名与入口合同](project-alias-contract.md) |
| `projectId` | 小写规范 UUID，版本 1—5，非全零 |
| `displayName` | 非空且不超过 128 字符，只用于展示，不能当作 UUID 或 subjectKey |
| `basis.kind` | `resume_claim`、`user_confirmed`、`source_learning` 之一 |
| `basis.key` | 非空且不超过 256 字符；指向来源依据，不是分数或评价 |

必须拒绝：未知字段、重复 JSON 键、非对象根、缺失字段、类型错误、`NaN`/`Infinity` 等非标准 JSON、超过 2048 字节、以及仅由模型猜出的“确认”。evidence 只承载这一个中性确认事实，不塞入源码、简历全文、录音、答案、评价或额外文件。

## 6. 禁止项

- 不记录次日回顾的提问、回答、提示或教练反馈；回顾零写入，不能用提纲或绑定旁路保存。回顾里提到、甚至确认了别名也不写 `project-binding`；确需配置，等回顾明确结束后单独确认。
- 不记录用户作答、分数、弱点、评价、`尝试次数` 或任何掌握度结论。
- 不写“已掌握”“掌握度”“得分”“评分”“分数”“弱点”“用户回答”“用户作答”“正确答案”等表现性措辞。
- 不记录只被计划、被排期、被提到但未实际讲授的内容。
- 不记录合成样例、测试夹具、其他项目或其他用户的内容。
- 不伪造 conversationId、teachingMessageId、projectId、unitId、projectAlias 或 sourceRef；定位不到时只保留在当前对话，并如实报告远端记录缺少来源依据。
- 不把教学提纲或别名绑定写进 `profileChanges`，不覆盖旧快照，不用 `supersede` 伪装“更新掌握度”。
- 不把同一别名写成两个 UUID、同一 UUID 写成两个活跃别名，也不用“最后写入获胜”掩盖冲突；本期不支持重命名、合并或多别名。
- 不上传源码仓库、私密文件或可识别的个人信息；不直接访问 Drive、D1 或 HTTP，不构造存储路径。

## 7. 事件形状

外层 envelope 使用既有 `schemaVersion:"1.2"`；内部 event 使用 `schemaVersion:"1.0"`。下面的示例全部是**占位结构**，UUID、时间与 sourceRef 必须替换为当次真实值，不能原样提交。身份只出现在 envelope 的 `identity` 中，不塞进内部 event。

构造器在 `software-project-learning/scripts/`：

| 维度 | 构造器 | 说明 |
|---|---|---|
| `learning-outline` | `project_evidence.build_outline_event` | 只返回内部 `{domain, event}` payload |
| `project-binding` | `project_context.build_project_binding_payload` | 只返回内部 `{domain, event}` payload；调用方自带 `eventId`/`eventKey`/`observedAt`/`sourceRef` |

两个构造器都不生成任何 ID、不发请求、不读投影。

```json
{
  "schemaVersion": "1.2",
  "namespace": "profile",
  "eventType": "profile.evidence.recorded",
  "identity": {
    "userId": "00000000-0000-4000-8000-000000000000",
    "username": "verified-display-name"
  },
  "payload": {
    "domain": "backend-project-learning",
    "event": {
      "schemaVersion": "1.0",
      "eventId": "00000000-0000-4000-8000-000000000003",
      "eventKey": "00000000-0000-4000-8000-000000000000:profile:backend-project-learning:project-binding:project-12306:00000000-0000-4000-8000-000000000003",
      "observedAt": "2026-10-23T02:10:00.000Z",
      "sourceSkill": "software-project-learning",
      "action": "observe",
      "observations": [
        {
          "dimensionKey": "project-binding",
          "subjectKey": "project-12306",
          "outcome": "observed",
          "evidence": "{\"bindingVersion\":1,\"projectAlias\":\"project-12306\",\"projectId\":\"00000000-0000-4000-8000-000000000000\",\"displayName\":\"12306\",\"basis\":{\"kind\":\"source_learning\",\"key\":\"confirmed-source:train-12306\"}}",
          "confidence": "high",
          "sourceRef": "project-confirmation:<conversationId>:<messageId>"
        }
      ]
    }
  },
  "requestId": "00000000-0000-4000-8000-000000000004"
}
```

同一 envelope 内的提纲 observation 形状如下（只列 observation，envelope 同上）：

```json
{
  "dimensionKey": "learning-outline",
  "subjectKey": "<projectId>:<unitId>",
  "outcome": "observed",
  "evidence": "余票展示：Controller 调用 V1，校验后按站点区域找候选车次，再逐车取价格、逐席别读余票；缺失时由 Loader 加锁、锁内二次检查、按区间与席别统计并回填。",
  "confidence": "high",
  "sourceRef": "learning-unit:<unitId>:<conversationId>:<teachingMessageId>"
}
```

实际提交时：

- 一个用户事实只提交一次；重试复用相同 `requestId`、`eventId`、`eventKey` 与完全相同的 payload 内容；
- 同键不同内容是冲突，不换 ID 掩盖；
- 不把回执前级当后级：`pending` 只表示本机排队，`d1_committed` 只表示 D1 接纳；
- 不写文件、不构造存储路径、不直接访问 Drive/D1/HTTP。

## 8. 读取与未知状态

读取顺序：`capabilities` → `user.resolve` → `projection.read`。分页保持同一 revision；`cursor_expired` 或 `projection_changed` 从第一页整次重读（最多重新开始一次，见 [项目别名与入口合同](project-alias-contract.md)），不拼接旧新页。

- `projection_not_found`、`building=true`、超时、分页不完整或读取失败都表示**历史未知**，不能解释为“没学过”“零分”“已掌握”或“从未绑定过”。
- 别名解析状态 `not_found` 只表示“完整读取后没有该别名的活跃绑定”，不是“该用户没有项目”。
- 别名解析状态 `unresolved`、`conflict` 时停止依赖历史或快照的操作，普通教学可以继续。
- 严格依赖昨日提纲的回顾应如实说明无可靠记录；不猜测、不补造提纲。

## 9. 修订与冲突

教学提纲是观察事实。后续讲授了同一 unit 的新框架时，追加新的 `observed` 事件，不覆盖旧事件；若要纠正错误提纲，以 `action:"supersede"` 引用已读取的 `targetEventKey` 提交新观察，或以 `action:"invalidate"` 作废。修正事件的 `observedAt` 必须晚于目标事件，不删除其他观察。目标未读到时不得提交修订。

别名绑定冲突的修复同样只能追加：对已读取的每个错误绑定逐个 `invalidate` 原 `eventKey`，保留不可变历史，再由用户确认正确映射。回顾期间不修复别名冲突；冲突未解决前不启动依赖该别名的正式读写。

## 10. 关闭与降级

- capabilities 未声明 `profile` 域：停止画像读写，继续普通教学，明确说明“画像未读取、未保存”。
- 身份解析失败或姓名不一致：停止画像写入，不绕过、不冒用其他用户。
- 工具缺失或服务不可用：保留当次提纲或确认，报告阻塞；不回退到 Drive、本地 JSON 或他人的画像。
- 别名解析不唯一（`unresolved`/`conflict`）：停止依赖别名的读写，普通讲解继续；不按相似名猜 UUID。
- 本 Skill 不自行判定弱点是否关闭；弱点的开启、改进与关闭由服务端依据项目作答与评价计算。

## 11. 与问答合同的分工

| 事实 | 唯一 owner | 事件 |
|---|---|---|
| 已讲授内容 | 本 Skill | `profile.evidence.recorded`（`learning-outline`，`observed`） |
| 别名确认 | 本 Skill | `profile.evidence.recorded`（`project-binding`，`observed`） |
| 正式作答 | 本 Skill（学习场景）或模拟面试 Skill | `interview.session.completed`（`project_learning`） |
| 评价 | 复盘 Skill | `interview.review.completed` |

正式作答的字段、attempt 规则、provenance、回顾零写入与独立通过定义全部以 [项目问答与证据合同](project-evidence-contract.md) 为准；别名语法与解析规则全部以 [项目别名与入口合同](project-alias-contract.md) 为准。本文件不复制这两份规则。模拟面试与复盘只**读**已确认的别名映射，不写绑定。
