# 题库快照合同

题库与每日题单保存在 `knowledge/java/resume-interview/学习快照.json`，写入方式遵守 [RDS-JBryon 运行契约](../../references/rds-jbryon-runtime.md)。题目覆盖 Java、MySQL、Redis、MQ 与简历明确提到的中间件。

题目关系为 `简历声明 -> 知识点 -> 规范题目 -> 推荐回答链 -> 评分要点`。每道题有稳定 `questionKey`、`knowledgePointId`、`resumeVersion`、简历声明引用、知识点、难度、来源标签和评分点；同一题库内 `questionKey` 唯一。

题面改写或调整表述时不得改变考点；只有考查的知识点或推理任务发生变化时才创建新的 `questionKey`。

每日默认五题：两道最低掌握度题、一道未考简历明示题、一道项目场景追问题、一道历史低分复测题。弱项优先按题目掌握度、知识点掌握度、复测间隔、简历相关度排序。证据不足时少出题并说明，不使用无依据的通用八股补齐。题单创建后当日不变。
