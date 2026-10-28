# 规划快照字段

规划状态保存在 `knowledge/study-planning/规划快照.json`，传输和状态规则遵守 [RDS-JBryon 运行契约](../../references/rds-jbryon-runtime.md)。快照不是事件流或身份画像。

保存维度：

| dimension | 内容 | 示例键 |
|---|---|---|
| `goals` | 用户确认的长期时长、预算和目标变更 | `daily-budget`、`morning-budget` |
| `preferences` | 用户明确确认的拆分、休息和优先级偏好 | `task-priority`、`rest-pattern` |
| `execution` | 带日期的窗口、专注时间、产出和中断 | `2026-10-20/12306` |
| `loadFeedback` | 用户明确报告的疲惫、恢复或无法继续 | `2026-10-20/fatigue` |
| `adjustments` | 用户明确接受的当日调整或未来目标变更 | `2026-10-20/remaining-halved` |

只记录用户明确说出的时间、产出、疲惫、恢复、偏好和目标变更。模型提出的建议、尚未发生的计划、由时长推断的能力、人格或健康判断都不写入。`Asia/Shanghai` 自然日用于计划归属。

用户纠正已保存事实时，在当前 revision 上追加一条带 `supersedes` 的修订记录，不覆盖历史；目标记录读不到时说明暂不能修订。用最小 patch 更新快照，并以真实的 `projected` 状态确认写入。
