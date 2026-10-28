# 规划规则

本文件是 `adaptive-study-planning` 的可执行策略，不是医学、心理学或普遍最优结论。规则可按用户明确指令调整；一次反馈不能证明长期容量。

## 1. 不可变边界

1. 初始长期目标是 600 分钟；四组预算是 240 / 180 / 60 / 120。
2. 当日降级不改长期目标；只有用户明确改长期目标才改未来默认值。
3. 已用窗口、已完成产出和实际超额保持原样；不靠改分母制造“原计划已完成”。
4. 未知就是未知，不用 0 填充；用户未报告专注时间，不推断专注时间。
5. 不把“建议”“计划过”“讲过”记成用户已完成、已掌握或已同意。
6. 不自动补欠账、不自动推迟就寝、不自动创建三天后的任务。
7. 时区固定 `Asia/Shanghai`；日期按用户所在自然日解释。

## 2. 计量口径

| 字段 | 含义 | 缺失时 |
|---|---|---|
| `planned_window_minutes` | 学习任务窗口，含窗口内约定的短休息；十小时按此口径 | 无法规划，先确认 |
| `reported_focus_minutes` | 用户明确报告的实际专注时间 | 记为未知，不填 0 |
| `reported_used_window_minutes` | 用户明确报告已经使用的任务窗口 | 记为未知，先澄清 |
| `budgeted_remaining_minutes` | 调整后剩余任务窗口 | 由计算得出 |
| `goal_daily_minutes` | 长期每日目标，初始 600 | 使用已确认目标 |
| `effective_day_minutes` | 当日调整后的总预算 | 由计算得出 |

“今天学了六小时”没有说明是窗口还是专注时间，且会影响计算时，只追问口径，不猜。窗口时间、专注时间和产出数量不合并成一个“努力分”。

## 3. 决策优先级

用户最新明确指令 > 当前有效的确认偏好 > 当日明确反馈 > 已保存的历史证据 > 本文件默认建议。

历史证据不能覆盖用户当前明确选择。用户纠正事实时保留修订关系，不删除原观察。

## 4. 状态转移

| 输入或条件 | 当次动作 | 画像与长期目标 |
|---|---|---|
| 首次初始化，或已有目标但没有当日疲惫反馈 | 按 600 分钟目标输出计划 | 不预设今天疲惫 |
| “有点累”，未提出调整，严重程度不明 | 给短休息建议；只问一个影响后续安排的问题 | 记用户原话，不自动永久降级 |
| 明确“剩余任务减半”，且剩余预算已知 | 仅将尚未执行部分减半，已完成和已用部分不动 | 记当日临时调整；长期目标仍 600 |
| 明确“今天改成八小时或五小时” | 按指定当日总预算重排；已用超过新预算则不追加 | 不改长期目标；不抹去实际超额 |
| 休息后仍明确无法继续，或说“今天停止” | 结束当日任务，保留成果与下次入口 | 记停止反馈；不劝补课、不追问新知识 |
| 反复疲惫或多次中断 | 展示有日期的原始记录，提出次日减量建议 | 不诊断人格，不凭一次反馈断言长期容量 |
| 昨日降级，今天明确说“恢复十小时” | 恢复原预算 | 记录恢复指令，不视作永久加量 |
| 昨日降级，今天没有说明状态 | 先用一句话核对今天预算，不自动满负荷恢复 | 降级不是永久改目标，也不是无条件次日复位 |
| “以后每天改为八小时” | 更新未来长期目标至 480，保留变更前后值与生效日 | 属于明确目标变更，不能继续强制十小时 |
| 一段未完成或漏打卡 | 从当前可用窗口重排；未完成记未完成，未知记未知 | 不滚动累积全部欠账，不推断消失原因 |

当次明确调整不反复要求确认。涉及日期、口径或调整范围的关键歧义，最多先问一个必要问题。

## 5. 重排规则

1. 保留已使用窗口和已完成产出。
2. 剩余任务分钟数都非负，分配之和必须等于新的剩余预算。
3. `剩余预算 = max(0, 当日新总预算 - 已用窗口)`。已用口径未知时先澄清，不填零。
4. 用户指定的优先任务先满足；预算不足以覆盖优先任务时明确报告，不静默削减优先项。
5. 取整到五分钟：先按窗口权重分配整数个五分钟单位，用最大余数法补齐；余数相同按任务原顺序。最后不足五分钟的余量单列为 `wrap-up` 收束窗口，不强凑成学习任务。
6. 整个剩余预算不足五分钟时，只给一个 `wrap-up` 窗口。
7. 今天晚了不自动推迟就寝。用户要求熬夜追赶时，先说明现有窗口能完成的范围，不把延长作息当默认方案。
8. 一天中的“上午/下午”不等于固定钟点。窗口已过时，不自动把它们判为失效、未完成或欠账；先核对今天剩余可用时间，或按用户明确选择的剩余窗口重排。没有结束时间时不虚构作息。
9. 三道算法题是目标数量，不是自动完成，也不自动等同于三道全新题；时间不足时列出未完成项。

## 6. 计算脚本

`scripts/planning_rules.py` 是纯计算模块：无网络、无存储、无身份解析，不读取画像，不写文件。入口：

```text
evaluate_plan(request: dict) -> dict
```

也支持标准输入一份 JSON、标准输出一份 JSON。畸形 JSON 返回非零退出码且不输出计划；合法 JSON 的业务错误仍以 JSON 返回并退出 0。

### 6.1 共同输入

| 字段 | 类型 | 说明 |
|---|---|---|
| `operation` | string | `initialize`、`halve_remaining`、`set_day_budget`、`set_future_goal`、`stop_day` |
| `business_date` | string | 上海日期，`YYYY-MM-DD` |
| `goal_daily_minutes` | integer 或 null | 当前长期目标 |
| `effective_day_minutes` | integer 或 null | 当前当日预算；`initialize` 可省略，默认等于目标 |
| `reported_used_window_minutes` | integer 或 null | 用户明确报告的已用窗口 |
| `remaining_tasks` | array | 每项 `task_key` 唯一、`window_minutes` 为非负整数；只含尚未执行部分 |
| `new_budget_minutes` | integer 或 null | `set_day_budget` 与 `set_future_goal` 必填 |
| `effective_from` | string 或 null | `set_future_goal` 必填 |
| `priority_task_keys` | array，可选 | 用户明确指定先满足的任务键；必须是现有任务键 |

未知值用 null，不用 0。`initialize` 要求 `reported_used_window_minutes` 明确为 0；已开始当天应改用其他操作。

### 6.2 输出

正常返回包含 `status: applied`、`operation`、`business_date`、`goal_daily_minutes`、`effective_day_minutes`、`reported_used_window_minutes`、`budgeted_remaining_minutes`、`remaining_tasks`、`change_scope`、`overrun_minutes`、`reason`。`change_scope` 为 `none`、`day` 或 `future_goal`。`set_future_goal` 另带 `future_goal`；`stop_day` 另带 `cancelled_tasks`。

`needs_clarification` 只返回 `status`、`missing_fields`、`reason`；`invalid_input` 只返回 `status`、`reason`。两者都不输出伪造的新计划。

### 6.3 操作

| 操作 | 前置事实 | 计算 | 长期目标 |
|---|---|---|---|
| `initialize` | 当天明确尚未开始；任务合计等于当日预算 | 原样返回当天任务，`change_scope: none` | 不变 |
| `halve_remaining` | 用户已明确要求剩余减半；已用与剩余一致 | 剩余总和向下取半，按权重重分 | 不变 |
| `set_day_budget` | 用户明确指定今天总预算 | 剩余 = max(0, 新预算 − 已用)；重分 | 不变 |
| `set_future_goal` | 用户明确改长期目标并给出生效日 | 未来生效则今天不动；生效日等于今天则同时改今天 | 改为新值 |
| `stop_day` | 用户明确今天停止 | 剩余归零，列出取消项 | 不变 |

一致性检查：`已用 + 剩余任务合计` 必须等于当前当日预算；不一致返回 `invalid_input`，先核对，不悄悄修正事实。

### 6.4 示例：剩余减半

输入：

```json
{
  "operation": "halve_remaining",
  "business_date": "2026-10-20",
  "goal_daily_minutes": 600,
  "effective_day_minutes": 600,
  "reported_used_window_minutes": 360,
  "remaining_tasks": [
    {"task_key": "Resume basics", "window_minutes": 60},
    {"task_key": "Interview review", "window_minutes": 60},
    {"task_key": "Algorithm", "window_minutes": 90},
    {"task_key": "Skill work", "window_minutes": 30}
  ]
}
```

输出要点：`effective_day_minutes: 480`、`goal_daily_minutes: 600`、`budgeted_remaining_minutes: 120`，四项为 30 / 30 / 45 / 15。

### 6.5 示例：已用超过新预算

已用 360、当日原预算 600、剩余 240，用户明确“今天总共五小时”（300 分钟）。输出 `effective_day_minutes: 300`、`budgeted_remaining_minutes: 0`、`remaining_tasks: []`、`overrun_minutes: 60`。已用 360 分钟保留，不输出负数。

### 6.6 示例：未来目标

今天 2026-10-20 仍按 600 分钟，用户说“以后每天八小时”。以 `new_budget_minutes: 480`、`effective_from: "2026-10-21"` 调用，输出仍为 `goal_daily_minutes: 600`、`effective_day_minutes: 600`，并附：

```json
{"future_goal": {"minutes": 480, "effective_from": "2026-10-21"}, "change_scope": "future_goal"}
```

### 6.7 示例：取整与收束

任务 10 / 10 / 10，剩余预算 20：最大余数法得到 10 / 5 / 5，总和 20。剩余预算 122 时，120 分钟按权重分配，余 2 分钟单列 `wrap-up: 2`。剩余预算 3 时，只返回 `wrap-up: 3`。

## 7. 日期与生效

- `business_date` 是本次规划所属的上海自然日。
- `effective_from` 早于当天：`invalid_input`，不做历史改写。
- `effective_from` 等于当天：目标与当天预算同时改；输出 `change_scope: future_goal` 并附生效日。
- `effective_from` 晚于当天：只改未来默认值，今天计划原样保留。
- 不根据“昨天降级”自动推导今天预算；先核对。
- 不自动把跨日未完成项滚入今天；需要用户明确选择。

## 8. 任务状态与完成证据

| 状态 | 何时使用 |
|---|---|
| `planned` | 已安排，尚未开始 |
| `in_progress` | 用户明确说正在做 |
| `reported_completed` | 用户明确说完成，但没有专业 Skill 的可核实结果 |
| `verified_completed` | 专业 Skill 给出可核实结果，且该结果确实覆盖本任务 |
| `partial` | 完成一部分，剩余如实保留 |
| `cancelled` | 用户停止或明确取消 |
| `unknown` | 没有反馈或口径不明 |

计划生成、模型讲解、建议清单都不构成完成证据。用户自报时间只进入执行反馈，不自动变成掌握度。

## 9. 澄清问题

只在关键事实缺失且影响计算时提问，一次一个：

- 已用窗口未知，且用户要求减半或改预算；
- “学了六小时”口径不明，且需要与预算相减；
- 用户要求改长期目标，但没有生效日；
- 用户要求优先任务，但该任务不在剩余清单或预算不足；
- 昨日降级、今天没有说明状态，需要核对今天预算。

不重复询问已确认事项；用户可直接修改拆分建议。

## 10. 已知限制

- 脚本不做自然语言理解；“有点累”本身不会自动触发减半。
- 脚本不判断任务质量、专业完成度或掌握度。
- 脚本不访问画像；画像读写由对话按画像契约执行。
- 脚本不能证明用户会按计划执行，也不预测长期坚持效果。
