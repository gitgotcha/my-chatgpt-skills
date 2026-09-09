---
name: reviewing-java-backend-interviews
description: Use when reviewing a mock or real interview for a user resolved by display name, through one immutable submit_event handoff with local JSON and Word output.
---

# Java 后端面试复盘


先读 [RDS V2 运行契约](references/rds-v2-runtime.md)。唯一远端工具为 submit_event；新对话先检查设备绑定。未绑定且用户明确要求个人功能时，通过 `account.register` 自助注册并使用网关返回的 userId/displayName；已绑定账户不得按姓名自动切换，只有用户明确要求时才切换。技能不直接访问 Google Drive、D1、R2 或云端 HTTP。身份解析失败时保留当前内容，不绕过解析继续读取历史。

## 会话读取与复盘

身份解析成功后依次调用：

1. `submit_event(interview.session.list)`，只展示时间、领域、类型和复盘状态摘要。
2. 用户选择会话后调用 `submit_event(interview.session.load)`，读取目标 schema-1.2 会话及有效复盘事件。
3. 保留原问题、原回答、追问关联、正确性、完整性、错误、遗漏、失分原因、更好的口述回答、参考答案、表达分析和变式复测。

复盘事件必须包含 `sourceSessionEventId`、`sourceType`、`evidenceType`、`evidenceConfidence`、`questionReviews`、`profileChanges`、`recommendations` 和 `applyProfileChanges`。`reviewVersion` 从 1 开始；修订时创建更高版本，不覆盖旧事件。

模拟会话的画像变化默认允许应用。真实会话必须明确询问用户是否确认：未确认时保存 `applyProfileChanges: false`；确认后创建下一不可变版本并设置为 `true`。只有结构化字段进入画像重建，自然语言报告不会改变画像。

## 唯一提交与本地输出

构造完整 `interview.review.completed` JSON 后只调用一次 `submit_event`。按 V2 运行契约保存实际 receipt 并报告处理阶段，不按 V1 deliveryState 字段判断。

本地复盘文件统一保存为：

```text
outputs/interview/<userId>/interview-<sessionId>-report.json
outputs/interview/<userId>/interview-<sessionId>-report.docx
```

本地报告只保留为本地派生输出，不上传云端，也永不作为画像输入。先用 `save_review_json` 写完整事件副本，再以该 JSON 作为 `create_review_report(report_json, report_docx)` 的唯一输入生成 Word，并执行渲染检查。Word 生成失败不回滚 JSON 或已提交事件；明确说明失败原因并保留可重试文件。
