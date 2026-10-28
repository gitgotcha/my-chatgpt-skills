# 模拟面试与复盘数据设计

模拟面试和复盘的持久化对象是 RDS-JBryon JSON 快照。项目定向训练使用 `project/<project-name>/学习快照.json`；通用面试练习使用用户确认的可读路径。两类流程都按统一 `interviews` 结构保存题目来源、用户原答、追问时间线、教练评价和修订历史。

RDS-JBryon 负责请求耐久化、并发合并、冲突提示和快照投影。Skill 负责维护内容语义与证据来源。调用形状与状态边界见 [`../../references/rds-jbryon-runtime.md`](../../references/rds-jbryon-runtime.md)。
