# Software Project Learning

一个统一的软件项目学习 Skill。源码、需求、架构规格或实施计划存在其一即可开始；面试训练作为可切换模式，而不是另一套重复的 Skill。

## 两种模式

| 模式 | 学习内容 | 回答反馈 |
|---|---|---|
| 项目学习 | 业务、数据、源码/模拟实现、可靠性与优化 | 遵守用户确认偏好后提出一道核心题；按 10 分标准评价理解 |
| 专业面试 | 完整项目学习能力，加面试追问与表达训练 | 面试评分、标准答案；STAR 按需开启 |

每个新业务链路先给可渲染 Mermaid 时序图，再通过贯穿案例和按真实顺序逐段注释的调用链解释。完整单元按“代入场景 → 时序图 → 源码定位 → 逐段/逐行注释 → 状态与反例 → 取舍与验证 → 可口述答案 → 底部一道追问”组织。表达幽默、循循善诱，但类比后回到真实机制。详见[详细单元讲解格式](references/detailed-lesson-format.md)与[完整单元输入/输出示例](references/examples/unit-2-complete-dialogue.md)。余票展示的完整合成单元见[余票查询完整对话样例](references/examples/ticket-query-rds-complete-dialogue.md)。范例里的技术结论属于 12306 案例；其他项目必须重新核对源码。

## 正式问答与回顾

- 次日先只读昨日框架，由用户先回忆，补缺后再开展当日计划；回顾问答与反馈**零写入**。
- 正式学习和模拟面试共用 RDS-JBryon 同一项目 JSON 快照；保存学习框架、源码锚点、面试题、原答及时间线。首答不可被润色稿覆盖，写入状态以真实 RDS 回执为准。

项目路由、快照结构、RDS 状态与冲突处理见[RDS-JBryon 项目快照契约](references/rds-jbryon-runtime.md)。用户用 `project-12306` 表示 `project/12306`，不需要提供 UUID。

## 材料与事实

- 只有源码：以实际实现为证据，标注推断。
- 只有需求或设计：讲方案并提供明确标注的模拟实现。
- 两者都有：对照设计与实现，指出差异。

默认只读，不自动修改项目、部署或保存长期掌握度。

## 入口与验证

- 执行规则：[SKILL.md](SKILL.md)
- 详细单元讲解格式：[detailed-lesson-format.md](references/detailed-lesson-format.md)
- 完整单元输入/输出示例：[unit-2-complete-dialogue.md](references/examples/unit-2-complete-dialogue.md)
- 余票查询完整单元样例：[ticket-query-rds-complete-dialogue.md](references/examples/ticket-query-rds-complete-dialogue.md)
- RDS-JBryon 项目快照契约：[rds-jbryon-runtime.md](references/rds-jbryon-runtime.md)
- 项目学习评分：[standard-mode.md](references/standard-mode.md)
- 专业面试训练：[interview-mode.md](references/interview-mode.md)
- 项目建模：[project-modeling.md](references/project-modeling.md)
- 源码追踪：[source-tracing.md](references/source-tracing.md)
- 可靠性与优化审查：[reliability-review.md](references/reliability-review.md)
- 可复制提示：[copy-paste-prompt.md](references/copy-paste-prompt.md)
- 行为场景：[behavior-scenarios.md](tests/behavior-scenarios.md)

在仓库根运行 `python -m unittest discover -s software-project-learning/tests -v` 检查包完整性；教学效果还需结合行为场景人工验证。画像合规用 `python profile-aware-skill-creator/scripts/validate_profile_skill.py --mode profile software-project-learning`。
