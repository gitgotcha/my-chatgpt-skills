# Java Resume Knowledge Learning

该 Skill 面向简历事实驱动的 Java 后端八股练习，覆盖简历声明、知识点、题库、每日题单、逐题反馈和掌握度变化。

跨会话数据保存在 `knowledge/java/resume-interview/学习快照.json`，通过 `rds` MCP 读写。简历文件不默认上传，只保存用户确认的简历声明和作答事实。没有快照时不伪造历史，不以通用八股填满题单。

## 目录

- [Skill](./SKILL.md)
- [简历证据规则](./references/resume-evidence-policy.md)
- [题库合同](./references/question-bank-contract.md)
- [反馈评分](./references/feedback-scoring-contract.md)
- [快照字段](./references/profile-storage-contract.md)
- [每日题单提示词](./references/daily-task-prompt-template.md)
- [RDS-JBryon 合同](../references/rds-jbryon-runtime.md)
