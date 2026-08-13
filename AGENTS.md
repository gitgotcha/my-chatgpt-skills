# Cloud task router

Read exactly one workflow before responding:

- LeetCode、算法、动态规划、回溯、代码复杂度：`algorithm-learning/SKILL.md`
- 学习后端源码、业务流程、项目面试：`backend-project-learning/SKILL.md`
- Java 后端模拟面试：`conducting-java-backend-mock-interviews/SKILL.md`
- 面试记录复盘、报告或画像更新：`reviewing-java-backend-interviews/SKILL.md`

For interview workflows, use only the configured `reliable-drive-sync` MCP for candidate and artifact data. For a new candidate, call `create_candidate`, show the returned candidate ID and summary, then obtain explicit user confirmation before `get_candidate_context` or any submission. If the MCP is unavailable, keep work in the conversation and state that it has not been persisted.
