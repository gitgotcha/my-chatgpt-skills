# 隔离云端烟测

状态：**未验证**。fake Drive 与临时目录只是测试替身；不得以本地模拟替代真实云端成功。

只有运行时提供隔离测试身份且用户确认时才执行本清单。普通 Skill 调用只验证本地 `deliveryState` 为 `cloud_accepted` 或 `pending`，不得把 Outbox 接收当作真实 Drive 冒烟成功；业务会话仍可保持 `review_pending`。

1. 使用完全虚构的隔离姓名注册测试用户，取得独立的 `userId`，不读取或修改真实用户数据。
2. 记录本次创建的规范路径与本地副本的完整路径：

   ```text
   users/<userId>/interview/events/event-<eventId>.json
   users/<userId>/interview/profile/snapshots/snapshot-<UTC>-<headEventId>.json
   outputs/interview/<userId>/interview-<sessionId>-report.json
   outputs/interview/<userId>/interview-<sessionId>-report.docx
   ```

3. 验证 `MOCK-*` 会话交接、统一复盘、自动画像应用和下一轮读取同一领域指导。
4. 验证 `REAL-*` 会话的待确认、确认应用和拒绝不应用三种状态。
5. 验证事件 JSON 与快照 JSON 都能从规范目录读回，父目录与内容哈希均匹配。
6. 验证本地 DOCX 可从本地副本渲染；本地报告不上传云端。
7. 只清理本次清单中明确创建的文件；任何目标不明确时停止清理。旧 namespace 目录只读，不得移动、覆盖或删除。
