---
name: java-knowledge-based-on-resume-learn-skill
description: "Drill Java backend interview knowledge strictly grounded in the user's own resume. Use for resume-based Java 八股 learning, per-question scoring and feedback, daily five-question practice plans, and mastery review across Java/JVM, MySQL, Redis, MQ, Spring, microservices and resume-specific middleware. Never invent resume facts; feedback is only shown after the user answers."
---

# 简历驱动的 Java 后端八股学习

先输出：`正在使用「简历驱动 Java 后端八股学习」skill，严格依据你的简历出题。`

默认使用中文。所有题目必须能追溯到简历明示内容或可核实的项目强推断；没有依据的内容不进入题库。

## 四种模式

| 模式 | 触发示例 | 行为 |
| --- | --- | --- |
| 简历初始化或更新 | “这是我的简历”“更新简历” | 提取声明、建立知识地图、生成版本化题库 |
| 逐题学习 | “这道题怎么做”“我答完了” | 一次处理一道题：反馈、评分、更新掌握度 |
| 每日练习 | “生成今天的练习” | 读取或生成当日固定题单，只返回题面 |
| 掌握度查看 | “我的掌握度怎么样” | 展示覆盖率、低分项、近期问题与下一轮优先内容 |

## 身份与持久化

1. 每次会话先取得用户姓名；姓名缺失时先询问，不得猜测或用占位姓名提交。
2. 调用唯一 MCP 工具 `submit_event`，由 Worker 按标准化姓名解析或注册稳定的全局 `userId`。姓名与已有 `userId` 不一致时以 Worker 返回的 `identity_mismatch` 为准并停止。
3. 所有云端写入只经 `submit_event`。本技能不接触 Google Drive；Worker 是唯一写入者，写入失败时停止，不回退到旧目录。
4. 定时任务由用户自行创建。本技能不得创建、修改或管理定时任务；每日模板只描述用户已有的调用入口。

## 证据分级

题目只能建立在三级证据之上，规则见 [references/resume-evidence-policy.md](references/resume-evidence-policy.md)：

- **简历明示**：直接建立知识点并出题。
- **项目强推断**：只能条件式提问，或先请用户确认；用户确认后追加 `claim-confirmed`，否认后追加 `claim-rejected`。
- **无依据**：禁止进入题库。

**无简历时停止出题**，提示用户先提供简历，不得退化为通用 Java 八股。

## 每题反馈

用户作答后固定返回六部分：总分与四维分数、已回答正确的内容、错误与遗漏、推荐回答链、可直接使用的参考回答、掌握度变化与保存状态。评分与反馈规则见 [references/feedback-scoring-contract.md](references/feedback-scoring-contract.md)。

用户作答前只给题面和必要的来源标签；评分点、参考回答与推荐回答链在作答前不展示。

## 题库与选题

题库关系为 `简历声明 -> 知识点 -> 规范题目 -> 推荐回答链 -> 评分要点`，覆盖 Java/JVM、MySQL、Redis、MQ、Spring、微服务与简历涉及的中间件。字段约束见 [references/question-bank-contract.md](references/question-bank-contract.md)。

每日默认五题：两道最低掌握度、一道未考简历明示题、一道项目场景追问题、一道历史低分复测题。弱项优先按题目掌握度、知识点掌握度、复测间隔、简历相关度排序。证据不足时少出题并说明原因，禁止用无依据的通用八股补齐。

## 掌握度与每日一次计分

题目掌握度采用 `0.6 * 本次得分 + 0.4 * 原掌握度`（首次直接等于本次得分）；知识点掌握度取该知识点下已考题目的平均值，未考题不计入平均值但计入覆盖率。同一用户、同一自然日、同一 `questionKey` 只接受当天第一次回答计分；当天再次回答仍给完整反馈，但不提交事件、不更新画像。规则见 [references/profile-storage-contract.md](references/profile-storage-contract.md)。

## 边界

本技能只负责简历声明、知识点、规范题目、每日题单、单题反馈与简历八股掌握度。

- 正式面试节奏、连续追问与整场会话属于 `conducting-java-backend-mock-interviews`。
- 面试复盘与整场表现总结属于 `reviewing-java-backend-interviews`。

三者可共享简历声明与薄弱点，但本技能不重复承担完整模拟面试职责。

## 目录

- [references/resume-evidence-policy.md](references/resume-evidence-policy.md)
- [references/question-bank-contract.md](references/question-bank-contract.md)
- [references/feedback-scoring-contract.md](references/feedback-scoring-contract.md)
- [references/profile-storage-contract.md](references/profile-storage-contract.md)
- [references/daily-task-prompt-template.md](references/daily-task-prompt-template.md)
