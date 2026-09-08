# V2 每日算法练习

按 [V2 运行契约](rds-v2-runtime.md) 完成 capabilities、user.resolve、algorithm/learning 分页读取。任务明确姓名、当地日期和 Asia/Shanghai；不得依赖旧聊天身份或恢复旧 V1 调度。

1. 画像不存在、分页损坏或 building=true 时说明尚不能依据完整历史推题，不写事件。
2. 同一 revision 下读取全部所需页，先检查当日题单；已存在时原样使用，首次题单不可变。
3. 未完成题在下一日优先，明确卡点/错题优先，7 天内同题不重复；已推过的未完成题作为继续练习提醒，不算新推送。
4. 生成 3–5 道与已学范围相关的中文题；有实际掌握分时低分优先，同分选最久未复习；无分数不能编造分数。
5. 题单通过 algorithm.daily-plan-created 提交：schemaVersion=1.2，payload.event 包含 eventId,eventKey,eventType,userId,username,localDate,planId,timezone,generatedAt,items，严格按后端字段约束。先冻结请求和题单；回执仅代表实际完成的阶段。
6. 输出题目、目标、角色和打卡格式，首次不泄露答案；用户明确反馈才新增学习事件。

技能不直接创建文件或扫描历史来更新云端画像。定时任务启停由用户单独提出，本次技能更新不自动开启调度。
