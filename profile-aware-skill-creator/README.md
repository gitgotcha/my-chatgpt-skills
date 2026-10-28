# Profile-aware Skill Creator

用于在明确请求下创建或更新可跨会话保存状态的个人 Skill。

## 持久化设计

新 Skill 的数据只通过 RDS-JBryon `rds` MCP 进入 JSON 快照。为每个 Skill 定义用户可读的多层路由、记录字段、可记录证据与隐私边界；能力文件以 `route: ["knowledge", "java", "jvm"]` 保存路径层级，`domain` 只作分类标签。用户提供 UUID、账户身份或底层节点标识不是输入要求。

新顶层目录或含义不明确的多层路由，先展示完整路径并让用户确认；用户明确要求创建该路径时视为确认。跨会话读取、最小 patch、请求状态、冲突处理按仓库共享的 [RDS-JBryon 运行契约](../references/rds-jbryon-runtime.md)。

## 开发者入口

- [Skill](./SKILL.md)
- [通用快照接口](./references/profile-authoring-standard.md)
- [可移植 Skill 规范](./references/portable-skill-standard.md)
- [验证器](./scripts/validate_profile_skill.py)

旧版事件、全局身份、Drive 目录和账户注册协议已退役；新 Skill 不得生成这些运行指令。
