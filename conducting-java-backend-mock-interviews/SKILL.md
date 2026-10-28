---
name: conducting-java-backend-mock-interviews
description: Use when conducting a Java backend mock interview grounded in the user's resume or a selected project snapshot, especially for ByteDance graduate-level practice.
---

# Java 后端模拟面试

项目学习与本 Skill 共用 RDS-JBryon 的可读目录快照。先读 [RDS-JBryon 项目快照契约](../software-project-learning/references/rds-jbryon-runtime.md) 与[简历和项目证据接入](references/candidate-profile-integration.md)。用户选 `project-12306` 时按 `project/12306` 路由；用户只需提供可读路径，不需要账户或内部 ID。RDS 不可用时说明本场不能读取/保存项目快照，不谎称成功；若用户仍愿意，可继续不依赖历史的模拟。

## 面试执行

- 一次只问一道主问题，可以对同一题连续追问；面试中不直接给完整标准答案。用户说“不知道”时保留原话，最多给一次启发式提示，再按用户选择继续。
- 有简历或项目材料时，题目必须优先挂钩用户真实简历声明与项目源码/设计；不得编造其个人职责、生产指标或经历。选题前检索近期公开面经/岗位题源，建立来源卡并按[联网题源与来源卡](references/web-question-sourcing.md)去重；搜索只证明“有人报告问过”，技术答案以目标源码、官方文档或可复现实验为准。
- 选题难度以**字节跳动校招 Java 后端**为训练标尺：能顺着主链路追到关键源码、状态与故障边界，并能在追问中分析并发/失败/取舍；不得声称掌握字节内部题库、面试官标准或录用线。用户选项目专项时，只围绕该项目，不用通用高频题凑数。完整模拟/专项的配题规则见[项目专项面试](references/project-targeted-interview.md)及[面试协议](references/interview-protocol.md)。
- 用户指定题数时按题数执行；没有指定时先给简短计划。一次只呈现一道题，等待回答后再追问或进入下一题。
- 每道题保留题面、来源、关联简历/源码证据、用户原始回答、追问与补答时间线。原答不可被润色稿替换；分析和评分必须引用用户实际说过的内容。答题前的“昨天框架复述”属于学习回顾，不是模拟面试作答，不记入快照。
- RDS 可用时，用户每答完一道题就把原答及时间线追加进同一 session 快照，再继续下一题，避免中断丢失；场末再追加评价。若写入尚未投影，如实报告并按运行契约查询同一请求状态，不重复创建逻辑记录。
- 结束时给出分项评价、最关键缺口、可复用参考答案和下一步训练点。仅在实际回答后，按快照契约把原答与本场必要结果追加到同一个项目快照；保存状态须依实际 `rds` 回执描述。

## 项目快照写入

项目专项 session 追加到 `project/<slug>/学习快照.json`，与项目学习共用；非项目 session 使用用户确认的 `interview/mock/<name>.json`。保留题目与原答时间线。先读取当前内容和 revision，再提交最小 patch；请求冲突时保留双方并让用户决定。路径、幂等、状态和冲突规则以 RDS-JBryon 契约为准。
