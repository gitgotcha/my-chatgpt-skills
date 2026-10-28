# 历史文件：项目别名与入口合同（UUID binding）

> **停用说明（2026-10-27）：** 本文描述旧 RDS-V2 的 `project-` → UUID binding 流程，已被当前 RDS-JBryon 可读目录路由取代。项目学习和 Java 模拟面试使用 [`rds-jbryon-runtime.md`](rds-jbryon-runtime.md)，其中 `project-12306` 直接映射到 `project/12306`；不要按本文查询/绑定 UUID。

本文件是 `project-` 别名的**唯一规则来源**：语法、完整读取预算、解析状态机、活跃证据解析、冲突处理与一致性边界。别名映射这一事实的存储形状见 [画像契约](profile-contract.md)（`project-binding` 维度）；正式作答、快照与评价仍以 UUID 走 [项目问答与证据合同](project-evidence-contract.md)。本文件不复制这两份合同的字段与流程。

## 1. 作用与边界

别名是用户可读的**选择键**，用来把“今天学 `project-12306`”翻译成一个稳定的 `projectId`。它本身不是：权限边界、namespace、`domain`、Drive 路径、Skill 文件夹名、快照键或事件字段。

- 正式 session、question、review DTO 里不增加 `projectAlias` 字段；它们只用解析出的 UUID 与 `basis`。
- 不因为改名而重写旧事件或创建新 UUID；改名等于一次新的用户确认，仍指向同一 UUID。
- 模拟面试与复盘只**读**已确认的映射；只有项目学习 Skill 写 `project-binding`。
- 解析不唯一时停止依赖别名/历史的操作；普通教学可以继续。

## 2. 别名语法

完整匹配（fullmatch，不是子串搜索）：

```text
project-[a-z0-9](?:[a-z0-9-]{0,54}[a-z0-9])?
```

- 前缀固定 `project-`；后缀 1—56 个字符，只允许小写 ASCII 字母、数字与内部连字符；总长 9—64。
- 不做任何规范化：**不** `lower()`、**不** URL 解码、**不**去空白、**不**做 Unicode 归一化；函数返回调用方传入的原字符串。
- 拒绝：末尾换行或空白、前后空格、任何大写、`/` 与反斜杠、`.` / `..` 点段、`%xx` 百分号编码、Unicode 全角或同形字符、零宽字符、连续 `-`、末尾 `-`、空后缀、超过 56 的后缀。
- 合法示例：`project-12306`、`project-pig-rpc`、`project-ragent`、`project-a`。
- 非法示例：`project-12306/`、`project-12306/prod`、`Project-12306`、`project--12306`、`project-12306%2F`、`project-12306\n`、`project-１２３０６`。

别名不是 UUID 的替身：`projectId` 必须是用户确认的稳定 UUID，不能由别名、路径、显示名或 commit 推导。

## 3. 中性绑定事实

一次绑定确认写成一条 generic 1.0 的 `observed` 观察：

| 项 | 值 |
|---|---|
| domain | `backend-project-learning` |
| dimensionKey | `project-binding` |
| subjectKey | 别名本身 |
| outcome | `observed` |
| confidence | `high` |
| sourceRef | `project-confirmation:<conversationId>:<messageId>` |
| evidence | 严格 JSON 文本，UTF-8 ≤ 2048 字节，五字段 |

五字段、字段约束与拒绝清单见 [画像契约 §5](profile-contract.md)。要点：`projectAlias` 必须等于 `subjectKey`；`projectId` 是小写规范 UUID；`basis.kind` 只能是 `resume_claim`、`user_confirmed`、`source_learning`；未知字段、重复键、非对象、类型错误一律拒绝。

绑定不是成绩：它不进入 `profileChanges`，不产生 attempt、review 或 session，也不改变任何掌握度结论。

## 4. 完整读取预算

解析别名前必须完成一次**完整**读取，顺序为 `capabilities` → `user.resolve`（凭据绑定核对，不注册、不切换）→ `projection.read`（`namespace=profile`、`projectionName=backend-project-learning`）。

| 预算项 | 值 | 含义 |
|---|---|---|
| 每页 limit | 50 | 固定请求值；generic 读取不附加尚未支持的 `projectId`/`rowKind` 过滤 |
| 最多页数 | 20 | 超过即 `unresolved`，不把前几页当完整历史 |
| 累计响应 | ≤ 5 MiB | 按 UTF-8 JSON 字节累计；超预算即 `unresolved` |
| revision | 所有页相同 | 混合 revision 一律 `unresolved`，不拼接旧新页 |
| building | 所有页 `false` | 正在重建即为历史未知 |
| nextCursor | 末页为 `null` | 末页仍有游标说明没读完 |

- 整次重启最多一次：`cursor_expired` 或 `projection_changed` 时从第一页重新开始，预算重置；仍失败则 `unresolved`，暂停依赖历史的操作。
- `projection_not_found`、超时、读取失败与分页不完整都表示**历史未知**，不能推断成“没学过”“没有项目”或“从未绑定过”。
- 同一 revision 的所有页共享同一份 summary；以末页 summary 为准，因为它与所有页属于同一 revision。

## 5. 解析状态机

解析结果是固定五键对象：`status`、`binding`、`revision`、`evidenceRefs`、`reason`。只有 `resolved` 带 `binding`（五字段对象），其余 `binding` 为 `null`。

| status | 含义 | 允许的后续动作 |
|---|---|---|
| `resolved` | 完整读取后，该别名只有一个活跃的五字段映射 | 可用该 UUID 读取提纲/快照，进入正式读写 |
| `not_found` | 完整读取成功，但该别名没有活跃绑定 | 不自动猜 UUID；按“历史无绑定”流程由用户确认具体 UUID |
| `unresolved` | 读取不完整或无法证明唯一：revision 变化、`building=true`、末页有游标、超页数/超字节、凭据或 summary 用户不一致、活跃引用缺失、活跃证据非法 | 暂停依赖别名的操作，普通教学继续 |
| `conflict` | 同一别名有多个不同的五字段值；或同一 UUID 有多个活跃别名；或 `basis` 不一致 | 停止自动路由，按 §8 修复 |

补充规则：

- `not_found` **只**表示“完整读取后没有该别名的活跃绑定”，不等于“该用户没有历史项目”：可能此前只听过课。
- `unresolved` 与 `not_found` 不可互换；把半页结果当成唯一映射是最严重的错误。
- 不允许“最后写入获胜”：同一别名出现两个 UUID 时是 `conflict`，不是取时间最新的那条。
- 只要完整读取中出现任何活跃绑定冲突，就停止自动路由（fail closed），即使被查询的别名本身看起来唯一。

## 6. 活跃证据解析

1. 遍历 summary 的成员桶（`observations` 等），取 `dimensionKey=project-binding` 的**全部**活跃成员，用各自的 `evidenceRefs` 作为活跃 `eventKey` 集合。
2. 对每个 `eventKey`，回到同一 revision 的 `event_activity` 行（`rowKey=eventKey`），从 `value.event.observations` 中取出 `dimensionKey` 与该成员 `subjectKey` 同时匹配的那条 observation。
3. 解析该 observation 的 `evidence` 与 `sourceRef`，得到五字段绑定。
4. 必须检查**所有**活跃别名，不只检查被选中的那个，否则会漏掉“同一 UUID 的另一个别名”。
5. `observation` 行是历史，不是当前事实：已 `invalidate`/`supersede` 的绑定不能靠 observation 行复活；`event_activity` 缺失或引用不完整一律 `unresolved`。
6. 活跃 observation 的 `outcome`/`confidence` 必须是 `observed`/`high`；其他值视为合同违规，`unresolved`。

## 7. 写入门禁与首次引导

绑定写入只能发生在**显式配置阶段**，且必须有可定位的确认：

- 回顾（次日框架回顾）恒为**零写入**：即使回顾里提到、甚至确认了别名，也不写 `project-binding`；确需配置，等回顾明确结束后单独确认。
- 教学、正式问答、评价、模拟面试阶段都不写绑定。
- 确认必须可定位为 `project-confirmation:<conversationId>:<messageId>`；定位不到就只在本轮上下文使用，并如实说明没有跨会话保存。
- `resolved` 且确认的五字段与活跃绑定完全相同时允许写入（相同事实的重复确认）。五字段不同则拒绝，因为那会制造冲突。
- `not_found`（投影存在但没有活跃绑定）走“历史无绑定”流程：调用方先读项目目录/旧提纲得到候选 UUID，请用户明确确认“就是这个项目、沿用该 UUID”；门禁要求 `candidateProjectId` 与绑定里的 `projectId` 一致、`reusesPreviousProject: true`、确认可定位，且请求别名与绑定别名一致，才允许追加一条中性绑定。没有候选 UUID、候选与绑定不一致、或用户只是笼统说“沿用之前项目”但没有具体 UUID 时，一律拒绝；不按相似名或时间猜。
- 首次使用的引导例外（仅在以下条件**全部**满足时）：`capabilities` 与身份核对成功、历史查询明确返回 `projection_not_found`、没有已知 `pending` 事件、用户明确要求创建一个独立的**新**项目。此时可说明“当前没有可读取的历史，不能据此证明从未记录过”，由用户确认新 UUID 与 `basis` 后建立绑定。
- 例外不适用于：`building`、超时、分页不完整、revision 变化、身份错误、已有冲突，以及用户说“沿用之前项目”。这些情况一律不新建 UUID。
- 写入后必须等该 `eventKey` 已在同一 revision 的活跃 `evidenceRefs` 中可见，才启动依赖别名的正式读写；`pending`/`d1_committed` 不算完成。

## 8. 冲突处理

冲突时保留全部不可变历史，用追加的方式收敛：

1. 立即停止依赖该别名的自动路由与快照读取。
2. 向用户展示每条活跃映射的来源：别名、UUID、`basis`、`sourceRef`。
3. 由用户确认正确映射，而不是由模型挑一个“看起来对”的。
4. 对每个错误的活跃绑定**逐个** `invalidate` 其原 `eventKey`（引用已读取的目标，`observedAt` 晚于目标）；不 `supersede` 成“更新掌握度”，也不改写历史事件。
5. 重新完整读取，确认只剩正确映射且 `resolved`，再恢复路由。
6. 回顾期间不修复冲突：回顾零写入，冲突修复放在回顾结束之后。

本期不支持重命名别名、合并项目或一个项目多个别名；需要这些能力时另立设计与服务端方案。

## 9. 一致性边界

本方案**没有**新增服务端唯一别名索引，因此不承诺原子唯一绑定：

- 两个客户端并发确认同一别名，可能产生两个不同 UUID 的活跃绑定；下一次完整读取会把它暴露为 `conflict`。
- 追加前重读并核验，投影后完整读回，是调用方的义务；读到“相同别名”不等于“本次写入已生效”。
- 冲突可恢复（invalidate 错误绑定 + 重新确认），但这不等于线性一致性。
- 需要严格多客户端唯一性时，必须另行设计服务端约束；不能在前端假装已保证。
- 冲突或投影未完成时，不启动依赖别名的正式读写，也不把别名写进正式 DTO。

## 10. 实现映射

`software-project-learning/scripts/project_context.py` 提供纯函数，均不做 I/O、不生成 ID、不发请求：

| 函数 | 职责 |
|---|---|
| `validate_project_alias` | 完整匹配语法，返回原字符串 |
| `parse_binding_evidence` | 解析并校验五字段 evidence |
| `resolve_project_alias` | 按本文件 §4—§6 从完整读取解析状态 |
| `build_project_read_plan` | 返回固定的 generic + 快照读取计划 |
| `build_project_binding_payload` | 构造中性 `observed` payload，不塞身份、不造 ID |
| `plan_project_binding_write` | 按 §7 放行或拒绝一次绑定写入 |

对应测试在 `software-project-learning/tests/test_project_context.py`。夹具全部为合成数据，不读个人画像，也不代表服务端已接受。
