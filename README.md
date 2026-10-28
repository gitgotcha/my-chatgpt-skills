# My ChatGPT Skills

面向乔炳源个人使用的 ChatGPT、Codex 与 WorkBuddy Skill 集合。各 Skill 保持职责清晰，并通过同一条单用户快照服务共享必要的长期状态。

## 持久化服务

RDS-JBryon 是唯一活动持久化服务。Skill 只调用 `rds` MCP，以用户可读路径访问 JSON 快照，例如：

- `project/12306/学习快照.json`
- `project/rpc/学习快照.json`
- `knowledge/java/jvm/学习快照.json`
- `knowledge/java/juc/学习快照.json`

用户不需要账户、姓名校验、UUID、nodeId 或 workspace epoch。读取现有路径前先按路径解析；创建新顶层目录或不明确路径时，先展示完整拟建路径并取得确认。各 Skill 的证据边界、隐私约束和学习规则仍由各自合同决定。

完整工具输入、快照读写、重试、冲突和状态语义见 [`references/rds-jbryon-runtime.md`](references/rds-jbryon-runtime.md)。没有 `projected` 状态就不能声称云端快照更新完成。RDS 不可用时，只能继续不依赖历史的工作，并明确说明未读取或未保存。

## Skill 导航

- 算法学习：`algorithm-learning/SKILL.md`
- 简历驱动的 Java 八股：`java-knowledge-based-on-resume-learn-skill/SKILL.md`
- 软件项目源码学习：`software-project-learning/SKILL.md`
- Java 后端模拟面试：`conducting-java-backend-mock-interviews/SKILL.md`
- Java 面试复盘：`reviewing-java-backend-interviews/SKILL.md`
- 自适应学习规划：`adaptive-study-planning/SKILL.md`
- 儿童摄影编辑：`child-photography-editing/SKILL.md`
- 显式创建或更新 Skill：`profile-aware-skill-creator/SKILL.md`

## 边界

- 不把源码、简历原件、儿童照片或本地报告作为快照默认上传。
- 保留用户原答、来源与修订历史，不把模型润色稿覆盖为用户原话。
- 只写用户明确表达或实际完成的事实；不从计划或模型推断掌握度。
- 历史设计、迁移计划与旧协议仅供审计，不是运行步骤；活动入口必须指向 RDS-JBryon。

## 验证

从本仓库根目录运行：

```bash
python -m unittest discover -s tests -p "test_*.py"
```

各 Skill 目录中可运行其独立合同测试。跨会话状态更新必须以 RDS-JBryon 的实际状态响应为准。
