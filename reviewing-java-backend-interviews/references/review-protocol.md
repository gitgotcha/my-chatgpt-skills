# 复盘快照协议

面试复盘数据按 [RDS-JBryon 运行契约](../../references/rds-jbryon-runtime.md) 保存为 JSON 快照。项目学习/项目面试复用 `project/<slug>/学习快照.json`；其它复盘使用用户确认的 `interview/reviews/<name>.json`。只复盘当前对话、用户提供的 transcript/notes，或用户明确选定路径可读取的记录。

逐题保留原始问题、原回答、追问/补答时间线、证据类型与可信度、正确性、完整性、错误、遗漏、失分归因、参考回答和下一步复测。修订时追加更高版本，不覆盖原复盘。模拟面试的画像变化可按既有规则写入；真实面试的画像变化先征求用户确认。

项目题按 `project-campus-v1` 评分，证据不足时标为 `unscored`；不能用提高 review version 冒充新一轮作答。练习复盘、真实复盘、复测作答分别标记来源，不把教练写的参考答案混入用户原答。

JSON 与 DOCX 报告只作为本地派生文件输出；不得自动上传 transcript、DOCX 或其它附件。只有快照状态实际返回 `projected` 才报告云端记录完成。
