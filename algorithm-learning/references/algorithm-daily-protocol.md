# 每日练习生成协议

独立定时任务必须带固定的姓名、运行日期和时区（`Asia/Shanghai`）；不依赖聊天上下文，也不读取或创建任务调度配置。

1. 调用 `submit_event` 提交 `system.user-registered` 或直接提交业务事件，由 Worker 按姓名解析或注册用户并锁定 `userId`。只列出该用户 `users/<userId>/algorithm/` 下的事件、画像快照与当日题单，不得读取其他用户目录。
2. 校验全部事件并按 `eventKey` 去重，保留最早有效记录。选择覆盖全部事件键的最新快照；没有该快照时从事件重建，并只创建新的 `snapshot-<UTC>-<headEventId>.json` 缓存。
3. 先计算未完成题。它们按“已延期次数、弱点严重度、原计划日期”排序并优先进入题单。
4. 总量为 **3～5**：无积压且近期完成稳定时为 5（1 薄弱复习 + 2 当前专题 + 2 综合/变式）；有未完成题或前一日完成不足时压缩为 3，保留未完成题并优先补齐薄弱复习、当前专题。
5. 选题时避免 7 日内重复同一题；Hot100、代码随想录与用户历史错误题为候选来源。当前专题来自 `currentTopic`；综合/变式必须关联至少一个已学专题。
6. 题单经 `submit_event` 的 `algorithm.daily-plan-created` 提交，由 Worker 只创建唯一文件
   `daily-plan-YYYY-MM-DD-<planId>.json`，落在 `users/<userId>/algorithm/plans/daily/`，并读回校验。
   本地回执只解释两级 Outbox：`deliveryState: "cloud_accepted"` 表示 D1 Outbox 已接收，`pending` 表示事件仍在 SQLite 等待重试；两者的 Drive 写入都异步完成。
   任一状态都**不宣称已同步画像或 Drive 已完成**，后续由 Outbox 自动恢复。
7. 输出仅包含今日 3～5 题、每题角色/目标、打卡格式与未完成题提示；不要泄露完整解答。

严格说明：D1 接收与 Google Drive 完成不是同一状态。追加式创建使最终事件事实具备原子可见性；快照和题单只是可重建缓存。Skill 不根据 Outbox 回执宣称 Drive 已完成。

当日题单首次创建后不可变：当天已存在题单时原样返回，不重新生成。任务只调用 `submit_event`，不得直接读写 Drive。
