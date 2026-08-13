# Cloud task router

Read exactly one workflow before responding:

- LeetCode、算法、动态规划、回溯、代码复杂度：`algorithm-learning/SKILL.md`
- 学习后端源码、业务流程、项目面试：`backend-project-learning/SKILL.md`
- Java 后端模拟面试：`conducting-java-backend-mock-interviews/SKILL.md`
- 面试记录复盘、报告或画像更新：`reviewing-java-backend-interviews/SKILL.md`

For interview workflows, use only the configured `reliable-drive-sync` MCP for candidate and artifact data. Call `find_or_create_candidate(displayName)` to directly reuse or create the exact-name Drive folder; the same name always identifies the same person. All reads and writes use `displayName`, not a candidate ID or a separate confirmation flow. Treat any MCP write error as terminal: keep work in the conversation, state that it was not persisted, and do not continue to the next persistent action.
