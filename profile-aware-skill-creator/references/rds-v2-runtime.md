# RDS V2 运行契约

所有跨会话身份、画像和业务事件只调用唯一 MCP 工具 `submit_event`。技能不直接访问 Drive、D1、HTTP 或构造存储路径。业务 envelope 的 `schemaVersion:"1.2"` 与存储版本 2 是不同概念；不要把写事件改成 schemaVersion 2。

## 身份与查询
V2 身份由服务器凭据绑定。姓名只用于注册时生成展示身份和后续一致性核对，不能替代服务端凭据。先调用：

```json
{"storageVersion":2,"operation":"capabilities","params":{}}
```

返回 `storageVersion:2` 与 `domains`；只有所需 namespace 启用才读取个性化数据。再核对姓名：

```json
{"storageVersion":2,"operation":"user.resolve","params":{"displayName":"乔炳源"}}
```

示例姓名必须替换成用户实际姓名。若设备已绑定账户，调用 `user.resolve` 核对返回的 `userId/displayName`；未绑定且用户明确要求使用个人功能时，先通过同一 `submit_event` 调用账户网关自助注册：

```json
{"storageVersion":2,"operation":"account.register","params":{"displayName":"实际姓名","requestId":"新UUID"}}
```

网关在本机生成并安全保存高熵凭据，只把一次 Bearer 证明发给 Worker；返回 `userId/displayName`，设备未绑定时自动绑定，已有绑定时返回 `created_not_selected`，绝不抢占当前账户。注册后以返回的 `userId` 和 `displayName` 建立本次上下文；用户明确要求切换时才调用 `account.switch`。不要提交 `system.user-registered`，不要把凭据放进消息、事件、日志或技能文件。

读取物化画像：
```json
{"storageVersion":2,"operation":"projection.read","params":{"namespace":"algorithm","projectionName":"learning","limit":20}}
```
映射：算法 = algorithm/learning；面试 = interview/interview；简历学习 = resume-knowledge/resume-knowledge；通用画像 = profile/<domain>。项目学习 domain 为 backend-project-learning；摄影文字偏好 domain 为 child-photography-editing。

返回 `revision,building,lastEventSeq,summary,entries,nextCursor`；每个 entry 有 `rowKind,rowKey,value`。只读 D1 当前激活代，不从 Drive 扫描历史或由技能重建快照。以原参数携带 nextCursor 逐页读取；分页 revision 必须一致；cursor_expired/projection_changed 重新从第一页读取，不能混合旧页。building=true 表示构建未完成，不能把旧代声称为最新。projection_not_found 表示尚无画像，不是已掌握或零分；根据当前用户明确目标开始普通学习，严格依赖历史的每日任务则报告无画像并停止。

面试列表：`{"storageVersion":2,"operation":"interview.session.list","params":{"limit":20}}`，返回 sessions/nextCursor。
面试详情：`{"storageVersion":2,"operation":"interview.session.load","params":{"sessionId":"实际会话ID"}}`，返回 session。复盘历史与选择版本使用 interview/interview 画像分页读取，不凭空推断 reviewVersion。

## 写入与回执
业务事实使用既有严格事件字段与 payload；每次新事实生成 requestId、eventId、eventKey，首次提交后冻结。重试保持全部 ID 和内容不变；同键不同内容是冲突，不换 ID 掩盖冲突。

```json
{"schemaVersion":"1.2","namespace":"algorithm","eventType":"algorithm.learning.completed","identity":{"userId":"核对返回的UUID","username":"核对返回的姓名"},"payload":{"event":{}},"requestId":"新UUID"}
```
此处 event 仅为形状示意，必须按领域契约填完整再提交。写入先落 V2 SQLite Outbox，经 /v2/events 到 D1，Queue 消费者更新投影并异步归档 Drive。一个用户答题事实只提交一次；不要为轮询构造业务事件。

按实际回执表达：
- `persistence.localOutbox:"pending"`：仅确认本机排队，receipt 可能为空。
- `persistence.localOutbox:"acknowledged"` 且 `receipt.cloudPersistence:"d1_committed"`：云端 D1 已接收，不能称 Drive 完成。
- `blocked` 或错误：报告阻塞原因，不称已保存成功。
- 不要求 V1 的 deliveryState/status/identity 嵌套响应，也不把 cloud_accepted 文案当作必有字段。

只读状态查询：
```json
{"storageVersion":2,"operation":"event.status","params":{"targetRequestId":"首次提交的requestId"}}
```
也可用 targetEventId，二者恰选一个。返回 projection=projected 才称已投影，archive=archived 才称事件已归档。事件归档不等于所有投影包已归档。event_not_found 可能仍在本机排队，不重造事件。普通技能可说明待处理后继续业务，无需持续轮询。

## 通用画像
只提交有明确证据且符合本技能记录条件的 profile.evidence.recorded；payload 为 {domain,event}，内部 event schemaVersion 为 "1.0"。保留 sourceSkill、eventId、eventKey、observedAt、action、observations；观察项包括 dimensionKey、subjectKey、outcome、evidence、confidence、sourceRef。没有掌握证据只用 observed/consulted。不把用户私密文件、源代码、儿童照片或图片可识别信息默认上传。

画像修订用 supersede/invalidate 新事件引用已核对的 targetEventKey；不能覆盖快照或旧事实。新生成的画像技能必须引用本 V2 查询/凭据/回执规则，不生成 V1 注册与路径访问流程。
