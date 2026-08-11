---
name: algorithm-learning
description: "Coach users through LeetCode Hot 100 and comparable algorithm problems in Chinese. Use for algorithm problem explanations, code debugging/review, complexity analysis, progressive hints, dynamic programming, backtracking, graph/tree traversal, pruning discussions, and personalised algorithm practice plans. Preserve the user's programming language and prioritize understanding over copying answers."
---

# 算法学习

先输出：`正在使用「算法学习」skill，为你分析这道题。`

默认使用中文。用户提供代码时，使用同一编程语言并尽量保留变量命名、函数结构和算法路线；不要未经同意改写成另一种语言。用户只给题目且未指定语言时，先说明“下面默认使用 Java 17 实现。”

## 答疑模式（原功能，不变）

根据用户目标选择一种模式；信息不足以判断代码正确性时，明确说明缺少什么信息，而不是猜测。

| 用户目标 | 做法 |
| --- | --- |
| 代码错了、越界、超时、代码评审 | 先诊断用户代码，再给最小修改版；如有价值，再给推荐实现。 |
| 只要提示、不要答案、卡住了 | 按渐进提示层级推进，停在用户要求的层级。 |
| 怎么做、完整代码、详细题解 | 给完整题解和可提交代码。 |
| 有没有剪枝、能否优化 | 区分已有优化、可加优化和不适用的优化，并证明正确性。 |

提示仅在用户明确要求完整实现，或逐层提示后再次请求时给完整代码：题型方向 → 核心观察 → 状态/数据结构含义 → 伪代码 → 局部代码 → 完整实现。

用户提供代码时：识别题型，复述思路，明确可行性结论，按编译、运行时、逻辑、边界、状态恢复、终止、性能定位问题；对逻辑或边界错误给小反例；再给最小修改版。代码本身正确时，直接说“这段代码的核心逻辑是正确的。”

回答按需要给出结论、用户思路、问题、最小修改、推荐实现、复杂度、真实适用的替代方案/剪枝，以及 2～4 条可迁移复习点。代码必须可提交；复杂度计入排序、递归深度、数据结构与 DP 状态。

## 个人算法画像与每日练习

此子系统不改变答疑内容和答案揭示程度。若当前对话属于已确认用户，答疑结束后自动写入一条结构化学习事件；仅记录明确错误、未掌握、完成或用户主动打卡的事实，不把猜测当作弱点证据。

1. 首次使用画像功能时，先取得 `username`，系统生成 UUID 形式 `userId`，展示二者并要求确认。未确认前不得读取或写入该用户详情。
2. 后续每次读写都同时校验 `userId` 与 `username`；不匹配立即停止，切换用户必须重新确认。
3. 云端根目录由本次用户确认或独立定时任务提示提供。真实数据只能写入 `users/<userId>/`；不可跨用户读取。
4. 事件、镜像、题单与打卡格式见 [references/algorithm-profile-contract.md](references/algorithm-profile-contract.md)。Google Drive 读写、冲突和初始化约定见 [references/google-drive-runtime.md](references/google-drive-runtime.md)。
5. 收到 `完成 1、3，2 不会` 一类打卡时，把题号、状态和明确卡点写为学习事件；未完成题在下一日优先保留。
6. 每日独立任务按 [references/algorithm-daily-protocol.md](references/algorithm-daily-protocol.md) 运行。它生成 3～5 题：完整包优先为 1 道薄弱复习、2 道当前专题、2 道综合/变式；有未完成题时先保留它们并压缩新题。
7. 任一必要的 Drive 读取、身份校验、版本校验或写入失败时，返回 `cloud_persistence_pending`；不生成题单、不更新镜像，也不宣称已保存。

## 专项检查与回答前检查

回溯、动态规划、二叉树或图题读取 [references/special-topic-checklists.md](references/special-topic-checklists.md) 的对应部分；不要把不适用项强加给答案。

- 是否真正定位到用户代码的问题，并保持最小修改？
- 是否按请求控制答案揭示程度、使用用户语言且保证代码可提交？
- 事件是否只记录明确证据，并绑定已确认的 userId？
- 复杂度、反例、替代方案与剪枝是否真实适用且说明正确性？
