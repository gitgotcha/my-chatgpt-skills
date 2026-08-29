# Google Drive 运行时存储约定

本项目已选择用户授权的 Google Drive 作为正式云端后端。**技能不直接读写 Drive**：所有云端写入只经 MCP 暴露的唯一工具 `submit_event`，由 Cloudflare Worker 执行。本 Skill 只构造事件内容、读取回执并生成本地报告。

## 唯一规范根

所有插件数据只写入：

```text
DriveRoot/my-chatGPT-skills/
├── user-registry/
│   └── registration-<userId>.json
└── users/<userId>/
    ├── identity.json
    └── interview/
        ├── events/
        └── profile/snapshots/
```

- 复盘事件由 Worker 追加到 `users/<userId>/interview/events/`。
- 画像快照由 Worker 物化到 `users/<userId>/interview/profile/snapshots/`。
- 读取遵循新路径优先、旧路径回退；旧 namespace 目录保持只读。

## 禁止的旧路径

当前流程中不再存在以下写入目标，任何恢复或回退都不得落到这些对象：

- 旧的全局候选人索引文件；
- 旧的候选人根目录及其个人子目录；
- 旧的当前画像指针文件；
- 原始 transcript 与 DOCX 报告的云端上传。

这些对象只允许出现在 legacy read-only 适配器、迁移说明或带有 archived/superseded 标记的历史文档中。

## 提交与校验

1. 先按姓名解析用户，取得规范化的 `{userId, username}` 绑定。
2. 构造唯一 `interview.review.completed` 事件，只调用一次 `submit_event`。
3. Worker 追加事件、读回校验父目录与内容，再物化快照。
4. 响应包含真实回执时标记 `persistenceStatus: "ok"`；整体写入失败标记 `cloud_persistence_pending`；事件已保存但快照失败标记 `profile_cache_pending`。

事件已存在而快照缺失时，用同一幂等键重试只会补做投影，不会重复追加事件。写入失败时停止，绝不回退到旧 namespace 目录，也不得把本地路径或测试替身称为已保存。

## 本地输出

本地只保留派生副本，不上传云端，也永不作为画像输入：

```text
outputs/interview/<userId>/interview-<sessionId>-report.json
outputs/interview/<userId>/interview-<sessionId>-report.docx
```

先用 `save_review_json` 写完整事件副本，再以该 JSON 作为 `create_review_report(report_json, report_docx)` 的唯一输入生成 Word。`create_review_report` 只接受 schema-1.2 的 `interview.review.completed` JSON，其余结构直接拒绝。
