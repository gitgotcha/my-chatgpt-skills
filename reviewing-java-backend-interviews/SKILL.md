---
name: reviewing-java-backend-interviews
description: Use when reviewing a mock or real Java backend interview, analyzing a transcript, scoring answers, or preparing a review report and follow-up practice.
---

# Java 后端面试复盘


先读共享 [RDS-JBryon 运行契约](../references/rds-jbryon-runtime.md)。只复盘当前对话中已有的模拟面试，或用户明确提供/选择的本地记录；不从已退役的服务枚举历史会话。需要跨会话保存时使用用户确认的可读路由与 `rds` MCP，不解析账户身份、不要求 UUID。人物画像仅由有来源的回答证据形成；不推断人格、稳定能力或求职适配度。

## 会话读取与复盘

复盘前确认输入会话来源；用户只要求复盘昨日或其他历史记录但没有提供可读路径/文件时，说明旧会话目录已退役并请其给出材料。保留原问题、原回答、追问关联、正确性、完整性、错误、遗漏、失分原因、更好的口述回答、参考答案、表达分析和变式复测。

复盘快照必须保留 `sourceType`、`evidenceType`、`evidenceConfidence`、`questionReviews`、`profileChanges`、`recommendations` 和 `applyProfileChanges`。每次修订追加新版本，不覆盖旧复盘或原始回答。快照是 JSON 内容，不是 `interview.review.completed` 事件或带身份字段的 ProfileSnapshot。

模拟会话的知识点变化默认可写入练习快照。真实会话必须明确询问用户是否确认应用画像变化：未确认时保存 `applyProfileChanges: false`；确认后追加新版本并设置为 `true`。只有结构化字段更新画像，自然语言报告不会改变画像。

## 项目合同

项目专项沿用对应项目的 `学习快照.json`，并额外遵守：

- 逐题评价写入 `questionReviews[].projectAssessment`：`attemptId` 必须属于该题，`rubricVersion` 固定 `project-campus-v1`，`scores`/`total` 按项目 rubric 计算或同时为 `null`，`outcome` 为 `passed`/`partial`/`failed`/`unscored`，`reason` 非空，`weaknesses` 逐项给出 `weaknessId`/`title`/`outcome`。
- `evidenceRefs` 必须指向该 session 内真实存在的内容：`<questionId>:originalAnswer` 或 `<questionId>:timeline:<messageId>`；指向不存在的内容即拒绝，不猜测。
- 项目面试的 `profileChanges` 必须为空数组：项目能力只从 `projectAssessment` 派生，不重复写入另一份全局画像。
- 撤回旧评价使用更高 `reviewVersion` 的 `unscored`（`scores=null`、`total=null`、`weaknesses=[]`），不修改历史；新复测必须新建 attempt/session，不能靠提升 `reviewVersion` 冒充。
- 纯八股与算法题沿用原 rubric，不塞入 `projectAssessment`；`mock`/`real` 的既有复盘规则不变。

## 保存与本地输出

对当前会话的复盘只写一次最小快照 patch；先读取目标快照和 revision，再按 RDS-JBryon 运行契约核验实际请求状态。项目专项复盘写回对应 `project/<slug>/学习快照.json`，并与项目学习/模拟面试共用快照；非项目复盘使用用户确认的 `interview/reviews/<name>.json` 路由。新建路由时展示完整路径并取得确认。RDS 请求中的 nodeId、revision、workspace epoch 与 requestId 由工具/Skill 流程管理，不向用户索要。

本地复盘文件统一保存为：

```text
outputs/interview/<sessionId>/interview-<sessionId>-report.json
outputs/interview/<sessionId>/interview-<sessionId>-report.docx
```

本地报告只保留为本地派生输出，不上传云端，也永不作为画像输入。先用 `save_review_json` 写完整报告，再以该 JSON 作为 `create_review_report(report_json, report_docx)` 的唯一输入生成 Word，并执行渲染检查。Word 生成失败不回滚快照更新；明确说明失败原因并保留可重试文件。
