---
name: adaptive-study-planning
description: Use when the user wants a daily study plan, a workload or time-budget change, an execution check-in, or recovery of their own planning profile across existing project, algorithm, interview, resume and Vibe Coding learning Skills. It plans totals, handoffs and execution feedback only, and never replaces the specialty Skill that teaches, scores or verifies the work.
---

# 自适应学习规划

只做总量规划、执行反馈、当日调整和规划画像。专业讲解、出题、评分、面试复盘和项目事实核验继续交给用户已有的专业 Skill。默认中文。

## 先判断本次动作

| 用户说法 | 本次动作 | 不做什么 |
|---|---|---|
| “列计划”“排今天” | 输出计划 | 不自动开课、不建对话、不发消息、不建定时任务 |
| “开始今天的 12306 / RPC / 算法…” | 输出交接卡，按对应专业 Skill 执行 | 不代替专业 Skill 讲解、出题或评分 |
| “用了 X 小时”“有点累”“今天停止” | 记录反馈，必要时重排 | 不把一次反馈升级为人格、疾病或长期能力判断 |
| “以后每天八小时” | 改未来目标，分开今天与以后 | 不悄悄改今天的预算，也不擦掉变更历史 |
| “按我的目标排” | 先读画像，再规划 | 读不到时如实报告，不伪造画像 |

用户只要求列计划时，不开始讲课、不创建新对话、不向其他对话发送消息。

## 读取规划画像

生成计划、调整预算或用户要求恢复历史前，先尝试读取已有目标与反馈；用户明确说“只按这次对话”时跳过读取并说明。按 [画像契约](references/profile-contract.md) 与 [RDS-JBryon 运行契约](../references/rds-jbryon-runtime.md) 执行：

1. 用 `kind=query` 的 `directory.resolve` 读取 `knowledge/study-planning/规划快照.json`；
2. 如路径不存在，先给出拟建完整路径并取得确认；用户明确要求创建该路径时视为已确认；
3. 读取快照内容与 revision 后再生成或调整计划，不把缺失数据当作零掌握。

工具缺失、读取失败或快照不存在时：仍可按本次对话明确给出的目标规划，并明确说“本次没有读取到历史”或“没有保存”。不推断零掌握，不回退到旧服务、全局记忆或本地 JSON 快照。

## 初始目标

用户已确认：每天 **600 分钟**，四组预算 `240 + 180 + 60 + 120`。

| 分组 | 预算 | 已确认内容 |
|---|---:|---|
| 上午 | 240 | 12306 两小时 + RPC 两小时 |
| 下午知识 | 180 | Vibe Coding、Agent 知识、基础八股合计三小时 |
| 面试复盘 | 60 | 需要真实会话材料，或明确标注为练习 |
| 晚上 | 120 | 算法与 Skill 沉淀/创建/学习合计两小时 |

下午各一小时、算法 90 分钟、Skill 30 分钟、“一道新题两道旧题”都只是**拆分建议**，不是已确认偏好。用户未确认前不写成个人偏好，也不据此拒绝调整。先试运行三天收集反馈，不自动创建三天后的任务。

## 生成或调整计划

关键数值用 [规划规则](references/planning-rules.md) 中的 `scripts/planning_rules.py` 计算；脚本不可用时按同一规则手算，并说明脚本未运行。未知值用 null，不用 0 填充。

操作只有 `initialize`、`halve_remaining`、`set_day_budget`、`set_future_goal`、`stop_day`。脚本不解析自然语言；只有用户的话已经明确对应某个操作时才调用。返回 `needs_clarification` 或 `invalid_input` 时先核对事实，不伪造新计划。

初始或完整计划输出：当前目标与依据、任务表、第一步、降级规则、画像状态。中途调整只输出变化前后、剩余安排、下一步和保存状态。

计划表使用“时段 / 内容 / 预算分钟 / 结束时留下什么”。表内分钟是**任务窗口**，包含窗口内约定的短休息；午间与晚间休息另留。`reported_focus_minutes` 与 `reported_used_window_minutes` 分开记录，不混算。

## 反馈与调整

完整状态转移表见 [规划规则](references/planning-rules.md)。默认行为：

- “有点累”但未要求调整：给短休息和当前最小步骤，只问一个影响后续安排的问题；不自动永久降级。
- “剩余减半”：只减尚未执行部分，已完成产出和已用窗口不动；当日预算随之下调，长期目标不变。
- “今天改成五小时或八小时”：按指定当日总预算重排；已用超过新预算时剩余为 0，不输出负数，也不抹去超额事实。
- “今天停止”：结束当日任务，保留成果与下次入口；不劝补课、不追加新知识。
- 前一天降级、今天没有说明状态：先用一句话核对今天预算，不自动满负荷恢复，也不把降级当成永久目标。
- “以后每天八小时”：从明确的生效日开始改长期目标；今天不变时保留今天的计划。

日期按 `Asia/Shanghai` 自然日解释。今天晚了不自动推迟就寝补课；没有结束时间时不虚构用户作息。时间已晚不等于上午/下午窗口自动失效，也不等于欠账；先核对今天还剩多少可用时间，再按明确窗口重排。

## 专业交接

按 [专业路由](references/skill-routing.md) 选择用户已有的专业 Skill。一次只交接一个主窗口和一条主线。交接卡至少包含：日期与任务键、专业 Skill、模式、窗口分钟、目标产出、已知材料或入口、明确未知项、停止条件、可返回证据。

计划中列出专业 Skill 不等于已经运行它。同一对话由 Codex 选择并读取对应 Skill；需要另开对话时只给可复制的交接卡，由用户打开，本 Skill 不创建或发送跨对话消息。

## 任务状态

`planned`、`in_progress`、`reported_completed`、`verified_completed`、`partial`、`cancelled`、`unknown`。这些是规划输出状态，不是画像 outcome。

用户只说“学完了”记 `reported_completed`；专业 Skill 给出可核实结果才用 `verified_completed`；模型讲过但用户未作答仍是 `planned` 或 `unknown`，不是完成或掌握。

## 记录边界

只写本 Skill 的 `planning-execution` 证据，不重复提交算法、面试、项目等专业事件，不用其他领域的分数推导“执行力分数”。只记录用户明确说出的时长、产出、疲惫、恢复、偏好和目标变更；建议、推测和计划本身不写成事实。写入规则、sourceRef 与修订方式见 [画像契约](references/profile-contract.md)。

## 不做什么

- 不诊断人格、疾病或长期能力，不宣称医学或普遍最优结论。
- 不自动创建提醒、定时任务、后台监控、对话或跨对话消息。
- 不直接访问 Drive、D1、R2 或云端 HTTP，不调用模型 API，不写本地画像快照。
- 不注册或切换账户，不修改项目源码。
- 只通过 RDS-JBryon 的 `rds` MCP 保存规划事实，不处理账户注册或用户切换。
- 不承诺“坚持十小时”；十小时是用户当前选择，可按明确反馈调整。

## 参考

- [规划规则](references/planning-rules.md)
- [专业路由](references/skill-routing.md)
- [画像契约](references/profile-contract.md)
- [RDS-JBryon 运行契约](../references/rds-jbryon-runtime.md)
- [完整合成样例](references/output-example.md)
