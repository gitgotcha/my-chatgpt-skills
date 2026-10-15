# Software Project Learning

一个统一的软件项目学习 Skill。源码、需求、架构规格或实施计划存在其一即可开始；面试训练作为可切换模式，而不是另一套重复的 Skill。

## 两种模式

| 模式 | 学习内容 | 回答反馈 |
|---|---|---|
| 项目学习 | 业务、数据、源码/模拟实现、可靠性与优化 | 遵守用户确认偏好后提出一道核心题；按 10 分标准评价理解 |
| 专业面试 | 完整项目学习能力，加面试追问与表达训练 | 面试评分、标准答案；STAR 按需开启 |

每个新模块先给 Mermaid 或关系表，再通过贯穿案例和按真实顺序讲解的调用链解释。源码教学同时提供关键代码块和独立的可点击绝对路径/起始行号索引。复杂单元可跨多轮讲；尊重用户确认门槛和当天可承受的学习量。详见[详细单元讲解格式](references/detailed-lesson-format.md)与[完整单元输入/输出示例](references/examples/unit-2-complete-dialogue.md)。范例里的技术结论属于 12306 案例；其他项目必须重新核对源码。优化不是模式路由条件；两种模式都能分析已有实现或未来方案。

## 材料与事实

- 只有源码：以实际实现为证据，标注推断。
- 只有需求或设计：讲方案并提供明确标注的模拟实现。
- 两者都有：对照设计与实现，指出差异。

默认只读，不自动修改项目、部署或保存长期画像。

## 入口与验证

- 执行规则：[SKILL.md](SKILL.md)
- 详细单元讲解格式：[detailed-lesson-format.md](references/detailed-lesson-format.md)
- 完整单元输入/输出示例：[unit-2-complete-dialogue.md](references/examples/unit-2-complete-dialogue.md)
- 项目学习评分：[standard-mode.md](references/standard-mode.md)
- 专业面试训练：[interview-mode.md](references/interview-mode.md)
- 项目建模：[project-modeling.md](references/project-modeling.md)
- 源码追踪：[source-tracing.md](references/source-tracing.md)
- 可靠性与优化审查：[reliability-review.md](references/reliability-review.md)
- 可复制提示：[copy-paste-prompt.md](references/copy-paste-prompt.md)
- 行为场景：[behavior-scenarios.md](tests/behavior-scenarios.md)

在仓库根运行 `python -m unittest discover -s software-project-learning/tests -v` 检查包完整性；教学效果还需结合行为场景人工验证。
