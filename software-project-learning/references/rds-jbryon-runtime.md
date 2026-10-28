# RDS-JBryon 项目学习与面试快照契约

项目学习与 `conducting-java-backend-mock-interviews` 共用此契约。RDS-JBryon 只为乔炳源提供单用户目录与 JSON 快照；项目路由是用户可读路径，用户无需提供任何内部标识。

## 路由和工具

- `project-12306` 是简写入口，对应路径数组 `['project','12306']`；`project/12306` 是正式目录路由。其他项目与知识主题可以多层嵌套，如 `project/rpc`、`knowledge/java/jvm`。保持用户明确给出的路径原样，不从相似名称猜测。
- 对用户已确认或本轮明确指定的路由，首次使用时自动补齐缺失目录与快照；不要求用户手工建文件夹。尚未确认的新顶层领域，先展示完整路径并确认；用户明确指定该完整路由即为确认。只读/禁止修改请求绝不触发自动创建。
- 唯一 MCP 工具名为 `rds`，通过 `kind=query` 读取、`kind=request` 提交写入、`kind=status` 查询本地请求状态、`kind=admin` 仅在需要 `task.retry` 时重试。先读 `capabilities` 了解协议与工作区 epoch；它不是用户身份，也不要求用户复制或记忆。
- 路径读取与自动补齐：从根开始逐层调用 `directory.list`，根目录传 `parentId:null`，后续层传上一层返回的 `nodeId`；按完整路径段精确匹配并分页读完。每个已存在节点沿用其 ID；缺失时，在路由已确认且本次允许写入的前提下，用 `directory.create` 依次创建顶层 `domain` 和中间 `directory`，用 `snapshot.create` 创建末尾快照，逐项等待 `projected` 后继续。只读请求遇到缺失路径时报告未找到，不创建。目录有歧义、分页不完整或返回错误时停止并说明，不猜节点。不要用会对未命中路径无响应的解析请求代替目录清单。完整路径定位后用 `snapshot.read` 读取当前 revision 与 JSON；整棵项目树用 `snapshot.query`。快照路径推荐 `project/<项目名>/学习快照.json`；用户已有明确文件名时沿用。
- 内部 `nodeId`、`requestId`、`workspaceEpoch` 由工具响应与协议处理。用户只需说可读路径；不得要求用户手工提供、查找或记忆 UUID。向工具提交时可复用工具刚返回的内部定位值，但不要把它变成对话入口或公开给用户作为操作前置。
- 写入请求必须依 RDS-JBryon 当前协议携带 `protocol:"rds-jbryon"`、`apiVersion:1`、当前 `workspaceEpoch`、唯一 `requestId`、`operation`、`target` 及必要的 `baseRevision`/`changes`。不能把 UUID 或工作区 epoch 当用户身份。

## 共用快照结构

一个项目的教学记录和模拟面试记录保存在同一份快照 JSON，按事实追加：

```json
{
  "schemaVersion": "project-learning-snapshot/1",
  "route": "project/12306",
  "project": {"displayName": "12306 购票系统", "basis": "source_repository"},
  "learning": {
    "units": [{
      "unitId": "ticket-availability-display",
      "title": "余票展示链路",
      "framework": ["入口", "库存缓存", "回源与返回"],
      "sourceRefs": [{"path": "服务端相对路径", "symbol": "方法名", "startLine": 1}],
      "status": "taught",
      "studiedAt": "ISO-8601"
    }]
  },
  "interviews": [{
    "sessionId": "工具生成的会话标识",
    "mode": "project_targeted",
    "difficulty": "ByteDance-campus",
    "completedAt": "ISO-8601",
    "questions": [{
      "questionId": "题目标识",
      "question": "原始题目",
      "sourceRefs": [],
      "originalAnswer": "用户首次原答",
      "followUps": [{"question": "追问", "originalAnswer": "用户补答"}],
      "assessment": {"score": 0, "feedback": "评价依据"}
    }]
  }]
}
```

示例仅定义概念形状，不要求一次创建所有可选字段。只记录真实学习/作答事实；用户没回答就不造答案或 interview item。首答、补答、评价分别追加或更新各自字段，绝不把润色稿覆盖原答。昨日回顾不属于正式 learning unit 或 interview session。

## 写入与状态

1. 每次更新先读取快照及 revision，再只提交本次发生变化的 JSON 路径；不要用旧快照全量覆盖。依赖中的目录/快照创建操作必须先实际生效。
2. 以路由路径做用户可读定位，创建文件时固定其父目录；重命名或移动后沿同一稳定节点继续，不因同名重建而改投新目标。
3. 每个写请求使用新 `requestId`；同一请求重试必须完全复用原 ID 与内容。按 `rds status` 或 `request.status` 的真实结果汇报阶段：`local_pending`、`waiting_dependency`、`delivery_blocked`、`d1_committed`、`projected`、`conflict`、`needs_attention` 等。只有 `projected` 才说快照修改已生效；本地排队或 D1 接收都不能说成已保存到可读快照。
4. 并发时独立字段变更可自动合并。同一字段出现不同修改时，读取冲突并保留双方，向用户解释差异并请其选择；选择后提交新的解决请求。不按最新时间戳覆盖，不丢弃任何一方。
5. RDS 工具、网络或快照查询不可用时，继续不依赖历史的教学；明确说明本轮未读/未写云端快照，并保留清晰待交接内容。不得回退到 UUID 画像、Drive、直接 HTTP/D1 或伪造成功回执。

## 次日回顾零写入

次日第一次进入项目学习时，先只读昨天 `learning.units` 的最近主体框架，请用户回忆；然后用简短补充修复遗漏，再给今天计划。该回顾本身不追加、不改写任何快照字段，也不构造面试题、尝试或评价。用户之后明确开始当天正式学习或模拟面试，才为新的实际内容追加快照。
