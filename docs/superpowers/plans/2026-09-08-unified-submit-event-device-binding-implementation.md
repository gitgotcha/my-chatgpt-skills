# Unified submit_event Device Binding Implementation Plan — Revision 2

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 仅用户明确授权后选择 superpowers:subagent-driven-development；本文件不自动派发代理。

**Goal:** 单一 submit_event 内分流账户、查询和业务写，持久绑定同机同Windows用户，防切换后误写。

**Architecture:** 账户控制库提供跨进程短事务互斥与持久版本，账户模块不依赖业务画像。业务传输在共同互斥下核对版本并接纳冻结事件，网络在锁外；Worker保持每请求凭据鉴权。

**Tech Stack:** Node22.22.2/26.7.0、node:sqlite、Windows DPAPI/PowerShell、现有Workers/D1/Miniflare4.20260730.0、MCP stdio。

**Spec:** [Revision 2 规格](../specs/2026-09-08-unified-submit-event-device-binding-design.md)。用户本轮确认编写计划；不是实现授权或审核通过证据。

## Global Constraints

- 单一MCP工具submit_event；不公开account_gateway工具。
- 本机同Windows用户首绑跨聊天/进程/重启，只有明确switch/unbind改变；凭据失效不换人。
- 姓名不是认证；每账户UUID，同名可独立；秘密不进MCP、日志或Git。
- 个人读写bindingContext匹配，Worker仍鉴权；不信任Agent上下文。
- 账户入口≤20、运行时总预算≤40、业务硬上限50；每invocation单预算器。
- 账户包≤4KiB；姓名1–80Unicode标量/≤320UTF8字节；业务包保持原限额。
- 配对≥128bit、10分钟单次、24小时同目标证明恢复；注册秘密≥256bit。
- 限流注册5/IP/h、兑换10/IP/10min、创建5/账户/h；故障关闭。
- 不修改已应用0006/0007，不删除既有V2数据，不恢复V1。

## 仓库与证据

S=C:/Users/27846/my-chatgpt-skills；M=C:/Users/27846/my-chatgpt-mcp-v2。所有文件前缀为仓库映射；执行命令在相应隔离工作区根。读取AGENTS和规格，执行前用using-git-worktrees隔离；保留M三份未跟踪审核文档。检查源码基线M=4f81009；现有LocalOutboxV2.enqueue同步且内部BEGIN IMMEDIATE，Bridge使用进程options.token，users.name_key UNIQUE，credentials是当前唯一users外键引用。执行前重查，事实改变则修订而非照抄。

12任务保留T00–T11标签便于对照，但内容及审核均新建。旧计划停用。顺序T00→T01→…→T11。G0=T00；G1=T01–T04；G2=T05–T07；G3=T08–T10；G4=T11。阶段门只汇总本任务门，不额外重复全仓审。

每任务开始前提供base SHA与测试设计，结束后提供head SHA、实际命令、退出码、原始脱敏输出。每一步先红后绿；首次因模块缺失红不足以证明业务反例，要补行为红。未执行未来任务的测试只能写“预期”。

## 存储与协调契约

本机control.sqlite位于当前Windows用户数据目录，ACL仅当前用户；设备秘密另用DPAPI。首次注册/current可创建控制元数据，不创建业务Outbox。表：
```sql
CREATE TABLE device_binding (
 singleton INTEGER PRIMARY KEY CHECK(singleton=1),
 installation_id TEXT NOT NULL, binding_epoch TEXT NOT NULL,
 binding_revision INTEGER NOT NULL CHECK(binding_revision>=0),
 user_id TEXT, credential_ref TEXT,
 CHECK((user_id IS NULL)=(credential_ref IS NULL))
);
```
首次installation/epoch为随机UUID，revision0；switch/unbind生成新epoch和revision+1，不修改installation；安全恢复备份生成新epoch，不能live覆盖产生ABA。账户元数据与加密意图按UUID引用独立文件，原子替换；find分页绑定元数据清单版本。T05网络验证在控制锁外，结果在锁内CAS；T06写接纳在同一控制锁内，不把网络持锁。共同锁仅协调，不使两个库假装成分布式事务；enqueue提交即事实持久化点。

D1新增表（UUID/哈希/时间边界由T01及服务层验证，SQL另约束关联、状态与事务）：
```sql
CREATE TABLE rds2_registration_intents (
 request_id TEXT PRIMARY KEY, proof_hash TEXT NOT NULL, input_hash TEXT NOT NULL,
 user_id TEXT NOT NULL REFERENCES rds2_users(user_id), created_at TEXT NOT NULL
);
CREATE TABLE rds2_pairing_tickets (
 code_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES rds2_users(user_id),
 source_credential_hash TEXT NOT NULL REFERENCES rds2_credentials(credential_hash),
 created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
 consumed_by TEXT UNIQUE, consumed_at TEXT,
 CHECK((consumed_by IS NULL)=(consumed_at IS NULL))
);
CREATE TABLE rds2_pairing_redemptions (
 request_id TEXT PRIMARY KEY, code_hash TEXT UNIQUE NOT NULL,
 proof_hash TEXT NOT NULL, user_id TEXT NOT NULL REFERENCES rds2_users(user_id),
 created_at TEXT NOT NULL, recover_until TEXT NOT NULL
);
CREATE TABLE rds2_account_limits (
 bucket_key TEXT PRIMARY KEY, attempts INTEGER NOT NULL CHECK(attempts>=1),
 expires_at INTEGER NOT NULL
);
CREATE INDEX rds2_ticket_expiry ON rds2_pairing_tickets(expires_at);
CREATE INDEX rds2_redemption_expiry ON rds2_pairing_redemptions(recover_until);
CREATE INDEX rds2_limits_expiry ON rds2_account_limits(expires_at);
```
T02新增BEFORE INSERT redemption守卫：必须存在ticket与NEW.code_hash匹配、consumed_by=NEW.request_id、consumed_at=NEW.created_at、expires_at>NEW.created_at，JOIN user active及source credential active；否则RAISE(ABORT,'pairing_invalid')。T03标量查询零来源产生NULL并失败，不能INSERT SELECT零行静默跳过触发器。清理ticket/redemption总物理行≤20且过24h恢复窗口，不清注册意图。限流桶按固定窗口进入key，UPSERT只增加attempts，同窗口不滚动延期。

## 审核模型与节奏

目标暂定当前Codex本机；工具清单于2026-09-08提供gpt-6-astra/high和gpt-5.6-sol/medium，均有本地源码/工具访问能力。Astra按插件默认用于critical/deep，Sol用于standard。成本仅相对定位（复杂任务/日常任务），实际价格未知，不声称最省价格；fallback均未验证。派发前重查。外部WorkBuddy/ZCode未验证库存，转交时必须核对ID、推理档位、文件工具权限，否则model=null/status=blocked_model_config，不能套用本机清单。

全部manual_handoff，全部pending，没有实际审核运行。critical前后两门；deep/standard仅post。审核只读不修改代码。输入缺失返回insufficient_evidence；每问题给位置、原始证据、影响、是否阻断和验证方法。修复只重审受影响diff，稳定旧版本证据不重复；相同阻断两轮未解人工裁定。模型不可用无已验证等能力替代则停止。风格/额外变异建议不阻断，真实规格/安全/数据/预算缺口仍阻断。审核不授权部署或推送。


## T00：Windows持久协调与安全输入验证

**Review level:** critical。

**Files:**
- M/tools/reliable-drive-sync-mcp/gateway/device-store.mjs
- M/tools/reliable-drive-sync-mcp/test/device-store.test.mjs
- M/docs/runbooks/device-binding-evidence.md

**Interfaces:** `openDeviceStore({path})->{current(),exclusive(fn),close()}`；exclusive 是同步回调，返回 Promise 或进行网络操作必须拒绝。创建独立 control.sqlite，不存业务内容。

- [ ] 读取本任务接口与前置证据，准备本任务失败场景；critical先通过PRE再改实现。
- [ ] 写目标行为红灯（使用本任务建立的夹具，样例断言如下，变量是该夹具结果，不是生产接口）：
```js
assert.throws(() => store.exclusive(() => Promise.resolve()), {code:'async_in_device_lock'});
```
- [ ] 在M运行 `node --test tools/reliable-drive-sync-mcp/test/device-store.test.mjs`，预期目标断言失败；记录原始输出，排除语法/夹具原因。
- [ ] 最小实现：控制库采用 SQLite BEGIN IMMEDIATE/COMMIT/ROLLBACK 做跨进程写锁；busy_timeout=5000，超时返回 device_busy。不用有到期时间的文件锁，避免慢进程仍活着却被夺锁。两个真实 Node 子进程竞争时临界区不重叠，kill 持锁子进程后操作系统释放 SQLite 锁；执行前/后点查持久绑定。用合成秘密验证 DPAPI 与安全窗口只走私有管道；无秘密 stdout、无窗口截图。不能证明 Windows用户隔离、进程崩溃恢复、安全输入或相对启动时停止。
- [ ] 核心实现约束：
```text
BEGIN IMMEDIATE -> 同步action -> COMMIT；异常ROLLBACK；不允许await
```
- [ ] 同一命令全绿后运行本任务涉及模块的既有回归；POST只在真实证据齐全时审核。不把计划代码块当完整实现。
- [ ] 显式提交本任务文件，禁止add -A：
```powershell
# M仓库根
 git add tools/reliable-drive-sync-mcp/gateway/device-store.mjs tools/reliable-drive-sync-mcp/test/device-store.test.mjs docs/runbooks/device-binding-evidence.md
 git commit -m "feat: t00 device binding deliverable"
```

### R2-T00-PRE

```yaml
review:
  id: "R2-T00-PRE"
  tasks: ["T00"]
  phase: "pre_implementation"
  after: ["plan_approved"]
  blocks: ["T00"]
  level: "critical"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "跨进程互斥、崩溃释放锁和OS隔离是后续身份安全前提"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T00 Files与Interfaces及前置门结论"
    - "实际源码base SHA、测试设计、风险与失败窗口分析"
  checks:
    - "Windows持久协调与安全输入验证的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "跨进程互斥、崩溃释放锁和OS隔离是后续身份安全前提，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T00相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T00-PRE，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T00的pre_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

### R2-T00-POST

```yaml
review:
  id: "R2-T00-POST"
  tasks: ["T00"]
  phase: "post_implementation"
  after: ["T00"]
  blocks: ["T01"]
  level: "critical"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "跨进程互斥、崩溃释放锁和OS隔离是后续身份安全前提"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T00 Files与Interfaces及前置门结论"
    - "base/head SHA差异、上述命令的实际版本/退出码/脱敏原始输出"
  checks:
    - "Windows持久协调与安全输入验证的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "跨进程互斥、崩溃释放锁和OS隔离是后续身份安全前提，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T00相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T00-POST，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T00的post_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

## T01：统一输入和绑定上下文

**Review level:** critical。

**Files:**
- M/shared/device-binding-protocol.mjs
- M/tools/reliable-drive-sync-mcp/test/device-protocol.test.mjs

**Interfaces:** `parseSubmission(input)->{kind,body,bindingContext}`；kind 为 account/query/write。`sameBinding(a,b)->boolean` 比较 installationId/epoch/revision/userId；`normalizeName(value)->string`。

- [ ] 读取本任务接口与前置证据，准备本任务失败场景；critical先通过PRE再改实现。
- [ ] 写目标行为红灯（使用本任务建立的夹具，样例断言如下，变量是该夹具结果，不是生产接口）：
```js
assert.throws(() => parseSubmission({storageVersion:2,operation:'account.current',params:{},eventType:'x'}), {code:'invalid_params'});
```
- [ ] 在M运行 `node --test tools/reliable-drive-sync-mcp/test/device-protocol.test.mjs`，预期目标断言失败；记录原始输出，排除语法/夹具原因。
- [ ] 最小实现：账户操作仅接受规格 account.* 白名单；query 白名单维持现有六操作，其中 capabilities 可无绑定。写入剥离 bindingContext 后交原 classifySubmission，不改原字段/哈希。schema 公布 oneOf 两个封闭分支，运行时重复检查；个人请求缺 context 抛 binding_context_required。account.current/find/register/transfer.redeem 按规格无需旧 context；bind/switch/unbind 在params中带expectedBinding；transfer.create顶层带bindingContext。UUID字段严校验；revision非负安全整数；unbound userId为null。normalizeName先查字符串，再NFKC/trim，1–80标量/≤320UTF8，拒绝Cc/Cs。
- [ ] 核心实现约束：
```text
exactlyOne(operationShape, eventShape); personal && !bindingContext => reject
```
- [ ] 同一命令全绿后运行本任务涉及模块的既有回归；POST只在真实证据齐全时审核。不把计划代码块当完整实现。
- [ ] 显式提交本任务文件，禁止add -A：
```powershell
# M仓库根
 git add shared/device-binding-protocol.mjs tools/reliable-drive-sync-mcp/test/device-protocol.test.mjs
 git commit -m "feat: t01 device binding deliverable"
```

### R2-T01-PRE

```yaml
review:
  id: "R2-T01-PRE"
  tasks: ["T01"]
  phase: "pre_implementation"
  after: ["R2-T00-POST"]
  blocks: ["T01"]
  level: "critical"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "协议混合分支或自动填当前UUID会绕过旧上下文保护"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T01 Files与Interfaces及前置门结论"
    - "实际源码base SHA、测试设计、风险与失败窗口分析"
  checks:
    - "统一输入和绑定上下文的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "协议混合分支或自动填当前UUID会绕过旧上下文保护，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T01相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T01-PRE，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T01的pre_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

### R2-T01-POST

```yaml
review:
  id: "R2-T01-POST"
  tasks: ["T01"]
  phase: "post_implementation"
  after: ["T01"]
  blocks: ["T02"]
  level: "critical"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "协议混合分支或自动填当前UUID会绕过旧上下文保护"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T01 Files与Interfaces及前置门结论"
    - "base/head SHA差异、上述命令的实际版本/退出码/脱敏原始输出"
  checks:
    - "统一输入和绑定上下文的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "协议混合分支或自动填当前UUID会绕过旧上下文保护，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T01相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T01-POST，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T01的post_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

## T02：D1同名账户迁移

**Review level:** critical。

**Files:**
- M/services/reliable-drive-sync-worker/migrations/0008_rds2_device_accounts.sql
- M/services/reliable-drive-sync-worker/test/device-account-schema.test.js
- M/services/reliable-drive-sync-worker/test/support/rds2-d1.js

**Interfaces:** 新增 `withDeviceAccountsD1(callback)`，保留原withD1。账户及管理表遵守本计划§存储契约；不复用旧按姓名初始化。

- [ ] 读取本任务接口与前置证据，准备本任务失败场景；critical先通过PRE再改实现。
- [ ] 写目标行为红灯（使用本任务建立的夹具，样例断言如下，变量是该夹具结果，不是生产接口）：
```js
assert.equal((await db.prepare('PRAGMA foreign_key_check').all()).results.length, 0);
```
- [ ] 在M运行 `node --test services/reliable-drive-sync-worker/test/device-account-schema.test.js`，预期目标断言失败；记录原始输出，排除语法/夹具原因。
- [ ] 最小实现：先写同名两UUID在旧schema失败的红灯；迁移新建users_next取消name_key UNIQUE，复制users；新建credentials_next FK指向users_next并复制；先删旧credentials再users，改名新表并重建索引。每次执行先检索新增FK；非已知引用则停下。使用真实D1迁移事务，不foreign_keys=OFF、不改0006/0007。填充原V2数据逐字段比较迁移前后，注入中间失败保证回滚。管理表和配对守卫见§存储契约，原用户UUID/凭据和全部业务表保持。
- [ ] 核心实现约束：
```text
copyParentsAndChildren -> dropChildBeforeParent -> rename -> verifyAllRowsAndForeignKeys
```
- [ ] 同一命令全绿后运行本任务涉及模块的既有回归；POST只在真实证据齐全时审核。不把计划代码块当完整实现。
- [ ] 显式提交本任务文件，禁止add -A：
```powershell
# M仓库根
 git add services/reliable-drive-sync-worker/migrations/0008_rds2_device_accounts.sql services/reliable-drive-sync-worker/test/device-account-schema.test.js services/reliable-drive-sync-worker/test/support/rds2-d1.js
 git commit -m "feat: t02 device binding deliverable"
```

### R2-T02-PRE

```yaml
review:
  id: "R2-T02-PRE"
  tasks: ["T02"]
  phase: "pre_implementation"
  after: ["R2-T01-POST"]
  blocks: ["T02"]
  level: "critical"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "迁移不可逆且影响现有所有账户和外键"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T02 Files与Interfaces及前置门结论"
    - "实际源码base SHA、测试设计、风险与失败窗口分析"
  checks:
    - "D1同名账户迁移的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "迁移不可逆且影响现有所有账户和外键，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T02相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T02-PRE，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T02的pre_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

### R2-T02-POST

```yaml
review:
  id: "R2-T02-POST"
  tasks: ["T02"]
  phase: "post_implementation"
  after: ["T02"]
  blocks: ["T03"]
  level: "critical"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "迁移不可逆且影响现有所有账户和外键"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T02 Files与Interfaces及前置门结论"
    - "base/head SHA差异、上述命令的实际版本/退出码/脱敏原始输出"
  checks:
    - "D1同名账户迁移的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "迁移不可逆且影响现有所有账户和外键，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T02相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T02-POST，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T02的post_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

## T03：注册与配对原子服务

**Review level:** critical。

**Files:**
- M/services/reliable-drive-sync-worker/src/rds2/accounts/registration.js
- M/services/reliable-drive-sync-worker/src/rds2/accounts/pairing.js
- M/services/reliable-drive-sync-worker/test/device-account-services.test.js

**Interfaces:** `registerAccount({io,requestId,name,secret,now,uuid})`；`createPairing({io,principal,code,now})`；`redeemPairing({io,requestId,code,secret,now})`。返回UUID/姓名/状态，无秘密。

- [ ] 读取本任务接口与前置证据，准备本任务失败场景；critical先通过PRE再改实现。
- [ ] 写目标行为红灯（使用本任务建立的夹具，样例断言如下，变量是该夹具结果，不是生产接口）：
```js
assert.equal(first.userId, replay.userId); assert.notEqual(first.userId, sameNameNewIntent.userId);
```
- [ ] 在M运行 `node --test services/reliable-drive-sync-worker/test/device-account-services.test.js`，预期目标断言失败；记录原始输出，排除语法/夹具原因。
- [ ] 最小实现：注册按requestId查幂等记录，proof_hash=SHA256(secret)、input_hash=canonical姓名hash；不存在则一次batch写users/credentials/intents，UNIQUE最多重查一次。相同ID不同proof/name冲突；重放检查账户及凭据active。配对码由来源运行时生成32随机字节，服务端只存hash、10分钟有效，同来源同码重试不延期。兑换先重查同requestId/proof/code恢复记录；新兑换条件UPDATE ticket→INSERT redemption VALUES标量查询user_id→INSERT credential VALUES标量查询user_id，一个batch。零行来源造成NOT NULL/触发器失败，不能零行INSERT SELECT跳过守卫。并发只有一个赢，同目标秘密24h恢复不再写凭据；来源撤销阻止新兑换。
- [ ] 核心实现约束：
```text
lookupProof -> atomicBatch -> boundedOneRecheck; neverFallbackByName
```
- [ ] 同一命令全绿后运行本任务涉及模块的既有回归；POST只在真实证据齐全时审核。不把计划代码块当完整实现。
- [ ] 显式提交本任务文件，禁止add -A：
```powershell
# M仓库根
 git add services/reliable-drive-sync-worker/src/rds2/accounts/registration.js services/reliable-drive-sync-worker/src/rds2/accounts/pairing.js services/reliable-drive-sync-worker/test/device-account-services.test.js
 git commit -m "feat: t03 device binding deliverable"
```

### R2-T03-PRE

```yaml
review:
  id: "R2-T03-PRE"
  tasks: ["T03"]
  phase: "pre_implementation"
  after: ["R2-T02-POST"]
  blocks: ["T03"]
  level: "critical"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "注册幂等和配对原子消费直接决定账户是否可被冒领"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T03 Files与Interfaces及前置门结论"
    - "实际源码base SHA、测试设计、风险与失败窗口分析"
  checks:
    - "注册与配对原子服务的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "注册幂等和配对原子消费直接决定账户是否可被冒领，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T03相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T03-PRE，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T03的pre_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

### R2-T03-POST

```yaml
review:
  id: "R2-T03-POST"
  tasks: ["T03"]
  phase: "post_implementation"
  after: ["T03"]
  blocks: ["T04"]
  level: "critical"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "注册幂等和配对原子消费直接决定账户是否可被冒领"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T03 Files与Interfaces及前置门结论"
    - "base/head SHA差异、上述命令的实际版本/退出码/脱敏原始输出"
  checks:
    - "注册与配对原子服务的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "注册幂等和配对原子消费直接决定账户是否可被冒领，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T03相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T03-POST，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T03的post_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

## T04：账户HTTP与预算限流

**Review level:** critical。

**Files:**
- M/services/reliable-drive-sync-worker/src/rds2/accounts/routes.js
- M/services/reliable-drive-sync-worker/src/rds2/accounts/limits.js
- M/services/reliable-drive-sync-worker/src/index.js
- M/services/reliable-drive-sync-worker/wrangler.toml
- M/services/reliable-drive-sync-worker/wrangler.production.toml
- M/services/reliable-drive-sync-worker/test/device-account-routes.test.js

**Interfaces:** `handleAccountRequest(request,env)`；`consumeLimit({io,bucket,window,max,now})`；`cleanupAccountRecords({io,now,limit:20})`。新增register/pairings/redeem HTTP，不新增MCP工具。

- [ ] 读取本任务接口与前置证据，准备本任务失败场景；critical先通过PRE再改实现。
- [ ] 写目标行为红灯（使用本任务建立的夹具，样例断言如下，变量是该夹具结果，不是生产接口）：
```js
assert.equal(response.status,429); assert.ok(trace.used<=20); assert.equal(unwrappedCalls,0);
```
- [ ] 在M运行 `node --test services/reliable-drive-sync-worker/test/device-account-routes.test.js`，预期目标断言失败；记录原始输出，排除语法/夹具原因。
- [ ] 最小实现：每入口一个createInvocationIo limit20，包括鉴权、限流、失败重查；4KiB流式读取超限cancel，secret仅HTTPS Authorization，码仅运行时HTTPS私有body。固定窗口D1 UPSERT RETURNING原子计次，bucket=HMAC服务器盐+可信边缘IP/账户+窗口；注册5/h、兑换10/10min、创建5/h。缺可信IP/盐/数据库返回503。新增开关ACCOUNT_OPERATIONS_ENABLED=false、ACCOUNT_SELF_REGISTER_ENABLED=false；账户current内部使用既有user.resolve并鉴权，capabilities新增无个人数据公共响应。清理独立有界调用，票据与兑换恢复窗口结束后成对删，总物理行≤20，intents保留。
- [ ] 核心实现约束：
```text
oneInvocationBudget(20); streamLimit(4096); atomicRateCounter; allFailuresCounted
```
- [ ] 同一命令全绿后运行本任务涉及模块的既有回归；POST只在真实证据齐全时审核。不把计划代码块当完整实现。
- [ ] 显式提交本任务文件，禁止add -A：
```powershell
# M仓库根
 git add services/reliable-drive-sync-worker/src/rds2/accounts/routes.js services/reliable-drive-sync-worker/src/rds2/accounts/limits.js services/reliable-drive-sync-worker/src/index.js services/reliable-drive-sync-worker/wrangler.toml services/reliable-drive-sync-worker/wrangler.production.toml services/reliable-drive-sync-worker/test/device-account-routes.test.js
 git commit -m "feat: t04 device binding deliverable"
```

### R2-T04-PRE

```yaml
review:
  id: "R2-T04-PRE"
  tasks: ["T04"]
  phase: "pre_implementation"
  after: ["R2-T03-POST"]
  blocks: ["T04"]
  level: "critical"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "公开入口和失败收尾必须受同一鉴权与预算约束"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T04 Files与Interfaces及前置门结论"
    - "实际源码base SHA、测试设计、风险与失败窗口分析"
  checks:
    - "账户HTTP与预算限流的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "公开入口和失败收尾必须受同一鉴权与预算约束，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T04相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T04-PRE，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T04的pre_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

### R2-T04-POST

```yaml
review:
  id: "R2-T04-POST"
  tasks: ["T04"]
  phase: "post_implementation"
  after: ["T04"]
  blocks: ["T05"]
  level: "critical"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "公开入口和失败收尾必须受同一鉴权与预算约束"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T04 Files与Interfaces及前置门结论"
    - "base/head SHA差异、上述命令的实际版本/退出码/脱敏原始输出"
  checks:
    - "账户HTTP与预算限流的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "公开入口和失败收尾必须受同一鉴权与预算约束，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T04相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T04-POST，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T04的post_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

## T05：安全账户意图与持久默认选择

**Review level:** critical。

**Files:**
- M/tools/reliable-drive-sync-mcp/gateway/secure-store.mjs
- M/tools/reliable-drive-sync-mcp/gateway/secure-dialog.ps1
- M/tools/reliable-drive-sync-mcp/gateway/accounts.mjs
- M/tools/reliable-drive-sync-mcp/gateway/device-store.mjs
- M/tools/reliable-drive-sync-mcp/test/device-accounts.test.mjs

**Interfaces:** `createAccounts({deviceStore,secureStore,client,dialog})->{current,find,register,bind,switch,unbind,transferCreate,transferRedeem,authorizeCurrent}`；`authorizeCurrent(expected)->{userId,context,credentialRef}`内部返回值。client为封闭HTTP适配器在accounts.mjs内创建，注入fetch测试。

- [ ] 读取本任务接口与前置证据，准备本任务失败场景；critical先通过PRE再改实现。
- [ ] 写目标行为红灯（使用本任务建立的夹具，样例断言如下，变量是该夹具结果，不是生产接口）：
```js
assert.equal(fetchCalls,0); assert.deepEqual(afterCancelled, before);
```
- [ ] 在M运行 `node --test tools/reliable-drive-sync-mcp/test/device-accounts.test.mjs`，预期目标断言失败；记录原始输出，排除语法/夹具原因。
- [ ] 最小实现：DPAPI加密秘密/意图，同目录临时文件flush后改名；UUID引用不接受路径。安全dialog用户主动操作才可见，其余辅助进程Hidden；管道取消/磁盘错误无开户请求。register/redeem先持久化同requestId意图再网络，完成后保存账户元数据；只有捕获的unbound版本仍匹配时CAS首次绑定，否则返回created_not_selected/bound_not_selected，不抢占其他进程选择。switch验证目标凭据在锁外，锁内比较四字段再epoch新UUID/revision+1。current读快照→在线验证→复核版本，不成功不返回authenticated；离线verification_unavailable保留选择。find只本机元数据分页20，cursor绑目录版本；恢复备份必须生成新installationId或epoch，禁止直接覆盖live控制库。
- [ ] 核心实现约束：
```text
verifyTargetOutsideLock; exclusive(compareExpectedThenPersistNewEpoch); failureKeepsOldBinding
```
- [ ] 同一命令全绿后运行本任务涉及模块的既有回归；POST只在真实证据齐全时审核。不把计划代码块当完整实现。
- [ ] 显式提交本任务文件，禁止add -A：
```powershell
# M仓库根
 git add tools/reliable-drive-sync-mcp/gateway/secure-store.mjs tools/reliable-drive-sync-mcp/gateway/secure-dialog.ps1 tools/reliable-drive-sync-mcp/gateway/accounts.mjs tools/reliable-drive-sync-mcp/gateway/device-store.mjs tools/reliable-drive-sync-mcp/test/device-accounts.test.mjs
 git commit -m "feat: t05 device binding deliverable"
```

### R2-T05-PRE

```yaml
review:
  id: "R2-T05-PRE"
  tasks: ["T05"]
  phase: "pre_implementation"
  after: ["R2-T04-POST"]
  blocks: ["T05"]
  level: "critical"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "默认账户跨进程变更和秘密恢复不能抢占用户选择"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T05 Files与Interfaces及前置门结论"
    - "实际源码base SHA、测试设计、风险与失败窗口分析"
  checks:
    - "安全账户意图与持久默认选择的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "默认账户跨进程变更和秘密恢复不能抢占用户选择，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T05相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T05-PRE，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T05的pre_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

### R2-T05-POST

```yaml
review:
  id: "R2-T05-POST"
  tasks: ["T05"]
  phase: "post_implementation"
  after: ["T05"]
  blocks: ["T06"]
  level: "critical"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "默认账户跨进程变更和秘密恢复不能抢占用户选择"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T05 Files与Interfaces及前置门结论"
    - "base/head SHA差异、上述命令的实际版本/退出码/脱敏原始输出"
  checks:
    - "安全账户意图与持久默认选择的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "默认账户跨进程变更和秘密恢复不能抢占用户选择，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T05相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T05-POST，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T05的post_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

## T06：接纳线性化与旧Outbox保全

**Review level:** critical。

**Files:**
- M/tools/reliable-drive-sync-mcp/gateway/business-transport.mjs
- M/tools/reliable-drive-sync-mcp/gateway/migrate-outbox.mjs
- M/tools/reliable-drive-sync-mcp/delivery-service-v2.mjs
- M/tools/reliable-drive-sync-mcp/test/device-outbox.test.mjs

**Interfaces:** `createBusinessTransport({deviceStore,accounts,outboxFactory,fetchImpl})->{query,submit,close}`；`migrateOutbox({source,targetRoot,deviceStore})`；复用现有LocalOutboxV2.enqueue与delivery。

- [ ] 读取本任务接口与前置证据，准备本任务失败场景；critical先通过PRE再改实现。
- [ ] 写目标行为红灯（使用本任务建立的夹具，样例断言如下，变量是该夹具结果，不是生产接口）：
```js
assert.equal(sentCredentialOwner,'A'); assert.equal(receipt.eventOwnerUserId,'A'); assert.equal(receipt.bindingChanged,true);
```
- [ ] 在M运行 `node --test tools/reliable-drive-sync-mcp/test/device-outbox.test.mjs`，预期目标断言失败；记录原始输出，排除语法/夹具原因。
- [ ] 最小实现：新submit先校验/捕获授权，deviceStore.exclusive内复核binding并同步enqueue进UUID分库；enqueue完成才释放控制库锁，所有switch也必须用同一锁。锁内不网络；若进程在enqueue提交后控制锁释放前崩溃，事实保留A，重放原ID返回原行。不需要两个库同事务提交绑定，因为接纳路径不修改绑定，控制库事务仅互斥。统一锁顺序control→outbox，后台只锁outbox，禁止反序死锁。读回包复核context；已接纳写后context变化返回最小回执owner+changed，不返回A画像或宣称零写入。后台凭据按冻结UUID，401暂停该账户投递保留行，重新合法绑定同账户才恢复。旧库先停服务/排他备份，按冻结UUID逐行幂等复制并比对所有状态时间hash/receipt，无法确认则全停；源保留不删，有效sending不改pending。
- [ ] 核心实现约束：
```text
control.exclusive(() => { 核对四字段; outbox.enqueue(frozenEnvelope); }); 网络只在释放后
```
- [ ] 同一命令全绿后运行本任务涉及模块的既有回归；POST只在真实证据齐全时审核。不把计划代码块当完整实现。
- [ ] 显式提交本任务文件，禁止add -A：
```powershell
# M仓库根
 git add tools/reliable-drive-sync-mcp/gateway/business-transport.mjs tools/reliable-drive-sync-mcp/gateway/migrate-outbox.mjs tools/reliable-drive-sync-mcp/delivery-service-v2.mjs tools/reliable-drive-sync-mcp/test/device-outbox.test.mjs
 git commit -m "feat: t06 device binding deliverable"
```

### R2-T06-PRE

```yaml
review:
  id: "R2-T06-PRE"
  tasks: ["T06"]
  phase: "pre_implementation"
  after: ["R2-T05-POST"]
  blocks: ["T06"]
  level: "critical"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "跨库接纳、账户切换及崩溃窗口是防误写核心"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T06 Files与Interfaces及前置门结论"
    - "实际源码base SHA、测试设计、风险与失败窗口分析"
  checks:
    - "接纳线性化与旧Outbox保全的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "跨库接纳、账户切换及崩溃窗口是防误写核心，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T06相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T06-PRE，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T06的pre_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

### R2-T06-POST

```yaml
review:
  id: "R2-T06-POST"
  tasks: ["T06"]
  phase: "post_implementation"
  after: ["T06"]
  blocks: ["T07"]
  level: "critical"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "跨库接纳、账户切换及崩溃窗口是防误写核心"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T06 Files与Interfaces及前置门结论"
    - "base/head SHA差异、上述命令的实际版本/退出码/脱敏原始输出"
  checks:
    - "接纳线性化与旧Outbox保全的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "跨库接纳、账户切换及崩溃窗口是防误写核心，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T06相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T06-POST，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T06的post_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

## T07：单MCP接线与四域兼容

**Review level:** critical。

**Files:**
- M/tools/reliable-drive-sync-mcp/stdio-bridge.mjs
- M/tools/reliable-drive-sync-mcp/start-v2.ps1
- M/tools/reliable-drive-sync-mcp/test/device-bridge.test.mjs

**Interfaces:** handleRequest复用现有入口；tools/list仅submit_event，账户registry调用T05的accounts，业务调用T06的businessTransport；不暴露credentialRef。

- [ ] 读取本任务接口与前置证据，准备本任务失败场景；critical先通过PRE再改实现。
- [ ] 写目标行为红灯（使用本任务建立的夹具，样例断言如下，变量是该夹具结果，不是生产接口）：
```js
assert.deepEqual(tools.map(x=>x.name),['submit_event']); assert.equal(personalIoWithoutContext,0);
```
- [ ] 在M运行 `node --test tools/reliable-drive-sync-mcp/test/device-bridge.test.mjs`，预期目标断言失败；记录原始输出，排除语法/夹具原因。
- [ ] 最小实现：将parseSubmission接入最外层；account.*走accounts，query/write走businessTransport。拒绝混合旧注册envelope，禁止V1回退。body剥离context后与旧业务canonical字节比较完全一致。先current再两业务调用，用户无重复确认；当前绑定失效服务器下一请求拒绝。payload嵌套身份不一致拒绝，不被顶层覆盖隐藏。start-v2改为用户目录自动解析，不加载固定乔凭据。四域分别测试查询和写入；账户模块import边界禁止业务reducer，工具描述不得承诺可直接调用其他插件。
- [ ] 核心实现约束：
```text
parse -> accountRegistry OR authorize+businessTransport; toolNameAlwaysSubmitEvent
```
- [ ] 同一命令全绿后运行本任务涉及模块的既有回归；POST只在真实证据齐全时审核。不把计划代码块当完整实现。
- [ ] 显式提交本任务文件，禁止add -A：
```powershell
# M仓库根
 git add tools/reliable-drive-sync-mcp/stdio-bridge.mjs tools/reliable-drive-sync-mcp/start-v2.ps1 tools/reliable-drive-sync-mcp/test/device-bridge.test.mjs
 git commit -m "feat: t07 device binding deliverable"
```

### R2-T07-PRE

```yaml
review:
  id: "R2-T07-PRE"
  tasks: ["T07"]
  phase: "pre_implementation"
  after: ["R2-T06-POST"]
  blocks: ["T07"]
  level: "critical"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "工具分流不能绕过绑定上下文或改变原业务哈希"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T07 Files与Interfaces及前置门结论"
    - "实际源码base SHA、测试设计、风险与失败窗口分析"
  checks:
    - "单MCP接线与四域兼容的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "工具分流不能绕过绑定上下文或改变原业务哈希，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T07相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T07-PRE，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T07的pre_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

### R2-T07-POST

```yaml
review:
  id: "R2-T07-POST"
  tasks: ["T07"]
  phase: "post_implementation"
  after: ["T07"]
  blocks: ["T08"]
  level: "critical"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "工具分流不能绕过绑定上下文或改变原业务哈希"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T07 Files与Interfaces及前置门结论"
    - "base/head SHA差异、上述命令的实际版本/退出码/脱敏原始输出"
  checks:
    - "单MCP接线与四域兼容的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "工具分流不能绕过绑定上下文或改变原业务哈希，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T07相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T07-POST，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T07的post_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

## T08：技能解耦与可移植包

**Review level:** deep。

**Files:**
- S/account-gateway/SKILL.md
- S/account-gateway/references/submit-event-authorization.md
- S/scripts/build-device-plugin.mjs
- S/tests/device-plugin.test.mjs
- S/docs/releases/device-plugin-inventory.md
- M/tools/reliable-drive-sync-mcp/build-device-release.mjs

**Interfaces:** 构建输入为当前Git与安装源逐项审定清单，输出runtime版本/hash和插件包。业务技能改动清单先写inventory再编辑，不按历史八个名字批量覆盖。

- [ ] 读取本任务接口与前置证据，准备本任务失败场景；critical先通过PRE再改实现。
- [ ] 写目标行为红灯（使用本任务建立的夹具，样例断言如下，变量是该夹具结果，不是生产接口）：
```js
assert.deepEqual(packagedNames, approvedInventory); assert.equal(exposedTools.length,1);
```
- [ ] 在S运行 `node --test tests/device-plugin.test.mjs`，预期目标断言失败；记录原始输出，排除语法/夹具原因。
- [ ] 最小实现：盘点当前安装8目录（含software-project-learning/review-model-routing）与Git源码，逐项记录保留/替换及来源SHA/文件hash。新增网关技能只讲account.*，不引用画像内容或领域schema。实际画像技能共同引用bindingContext契约，非画像技能不要求登录；profile-aware生成器同步验证器/模板/测试。构建脚本从已提交源产生插件清单/.mcp.json/runtime，不改市场文件手工路径；便携启动依赖T00真实证据。runtime精确版本/hash，不含凭据、Outbox或个人绝对路径；新Windows用户安装取消注册零副作用。
- [ ] 核心实现约束：
```text
inventory -> trackedSource -> pinnedRuntimeHash -> package -> freshWindowsValidation
```
- [ ] 同一命令全绿后运行本任务涉及模块的既有回归；POST只在真实证据齐全时审核。不把计划代码块当完整实现。
- [ ] 显式提交本任务文件，禁止add -A：
```powershell
# M仓库根
 git add tools/reliable-drive-sync-mcp/build-device-release.mjs
 git commit -m "feat: t08 device binding deliverable"
# S仓库根
 git add account-gateway/SKILL.md account-gateway/references/submit-event-authorization.md scripts/build-device-plugin.mjs tests/device-plugin.test.mjs docs/releases/device-plugin-inventory.md
 git commit -m "feat: t08 device binding deliverable"
```

### R2-T08-POST

```yaml
review:
  id: "R2-T08-POST"
  tasks: ["T08"]
  phase: "post_implementation"
  after: ["T08"]
  blocks: ["T09"]
  level: "deep"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "多个技能和发行包必须一致，但不是新账户授权算法"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T08 Files与Interfaces及前置门结论"
    - "base/head SHA差异、上述命令的实际版本/退出码/脱敏原始输出"
  checks:
    - "技能解耦与可移植包的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "多个技能和发行包必须一致，但不是新账户授权算法，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T08相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T08-POST，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T08的post_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

## T09：端到端与预算证据

**Review level:** deep。

**Files:**
- M/services/reliable-drive-sync-worker/test/device-acceptance.test.js
- M/tools/reliable-drive-sync-mcp/test/device-multiprocess.test.mjs
- M/docs/runbooks/device-acceptance.md

**Interfaces:** 生产HTTP/MCP入口+真实D1夹具+真实子进程；证据B01–B16，一条对应一个可复现结果，不以实现者叙述代替。

- [ ] 读取本任务接口与前置证据，准备本任务失败场景；critical先通过PRE再改实现。
- [ ] 写目标行为红灯（使用本任务建立的夹具，样例断言如下，变量是该夹具结果，不是生产接口）：
```js
assert.ok(trace.used<=20); assert.equal(trace.resets,0); assert.equal(foreignUserRows,0);
```
- [ ] 在M运行 `node --test services/reliable-drive-sync-worker/test/device-acceptance.test.js tools/reliable-drive-sync-mcp/test/device-multiprocess.test.mjs`，预期目标断言失败；记录原始输出，排除语法/夹具原因。
- [ ] 最小实现：合成A/B同名不同UUID，双设备配对；A写→另一进程switchB→旧context拒绝→A队列仍归A；kill在各提交窗口后恢复不丢/重复。真实Windows不同用户解密隔离、重启首绑复用、dialog未输出秘密记录人工步骤，未执行不能标通过。运行全部Worker/Bridge旧测试及新测试两Node版本；失败收尾计入trace。对账户模块依赖做静态禁导与模拟授权业务独立运行。记录未知能力为阻断而非猜测通过。
- [ ] 核心实现约束：
```text
productionEntrypoints + realChildProcesses + bothD1Bindings -> evidence B01..B16
```
- [ ] 同一命令全绿后运行本任务涉及模块的既有回归；POST只在真实证据齐全时审核。不把计划代码块当完整实现。
- [ ] 显式提交本任务文件，禁止add -A：
```powershell
# M仓库根
 git add services/reliable-drive-sync-worker/test/device-acceptance.test.js tools/reliable-drive-sync-mcp/test/device-multiprocess.test.mjs docs/runbooks/device-acceptance.md
 git commit -m "feat: t09 device binding deliverable"
```

### R2-T09-POST

```yaml
review:
  id: "R2-T09-POST"
  tasks: ["T09"]
  phase: "post_implementation"
  after: ["T09"]
  blocks: ["T10"]
  level: "deep"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "跨模块原始验收证据需要综合核对而非重复全仓代码审查"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T09 Files与Interfaces及前置门结论"
    - "base/head SHA差异、上述命令的实际版本/退出码/脱敏原始输出"
  checks:
    - "端到端与预算证据的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "跨模块原始验收证据需要综合核对而非重复全仓代码审查，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T09相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T09-POST，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T09的post_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

## T10：发布候选与操作手册

**Review level:** standard。

**Files:**
- M/docs/runbooks/device-release.md
- S/docs/releases/device-release.md

**Interfaces:** 输出准确执行顺序、候选runtime/skills提交hash、包hash、备份验证及回退策略；本任务不执行远程。

- [ ] 读取本任务接口与前置证据，准备本任务失败场景；critical先通过PRE再改实现。
- [ ] 写目标行为红灯（使用本任务建立的夹具，样例断言如下，变量是该夹具结果，不是生产接口）：
```js
assert.equal(release.defaults.selfRegister,false); assert.equal(release.defaults.adminInit,false);
```
- [ ] 在S运行 `node --test tests/device-plugin.test.mjs`，预期目标断言失败；记录原始输出，排除语法/夹具原因。
- [ ] 最小实现：候选产物测试在T08构建器中加入开关默认关闭、版本匹配和无绝对路径断言。手册明确先兼容身份代码暗部署→备份D1/旧本机→迁移→隔离canary→发行安装→公开开启。迁移失败回滚事务，已有同名账户后不能逆迁移UNIQUE或恢复旧管理员脚本。用户授权单列，签字/审核结果不等于部署执行成功。所有命令使用wrangler.production.toml，不用默认暗配置误覆盖。
- [ ] 核心实现约束：
```text
candidateHashes + explicitCommands + defaultOff + recoverableBackup -> reviewedRunbook
```
- [ ] 同一命令全绿后运行本任务涉及模块的既有回归；POST只在真实证据齐全时审核。不把计划代码块当完整实现。
- [ ] 显式提交本任务文件，禁止add -A：
```powershell
# M仓库根
 git add docs/runbooks/device-release.md
 git commit -m "feat: t10 device binding deliverable"
# S仓库根
 git add docs/releases/device-release.md
 git commit -m "feat: t10 device binding deliverable"
```

### R2-T10-POST

```yaml
review:
  id: "R2-T10-POST"
  tasks: ["T10"]
  phase: "post_implementation"
  after: ["T10"]
  blocks: ["T11"]
  level: "standard"
  status: "pending"
  model: "gpt-5.6-sol"
  reasoning_effort: "medium"
  execution_mode: "manual_handoff"
  reason: "冻结已有发布流程与版本证据，不包含执行不可逆动作"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T10 Files与Interfaces及前置门结论"
    - "base/head SHA差异、上述命令的实际版本/退出码/脱敏原始输出"
  checks:
    - "发布候选与操作手册的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "冻结已有发布流程与版本证据，不包含执行不可逆动作，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T10相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T10-POST，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T10的post_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

## T11：云端启用与GitHub交付

**Review level:** critical。

**Files:**
- M/services/reliable-drive-sync-worker/wrangler.production.toml
- M/docs/runbooks/device-release.md
- S/docs/releases/device-release.md

**Interfaces:** 消费T10候选和发布授权。输出生产版本、Git远端SHA、包hash与账户/业务各阶段回执。

- [ ] 读取本任务接口与前置证据，准备本任务失败场景；critical先通过PRE再改实现。
- [ ] 写目标行为红灯（使用本任务建立的夹具，样例断言如下，变量是该夹具结果，不是生产接口）：
```js
assert.equal(receipt.userId, syntheticUserId); assert.equal(realUserWrites,0);
```
- [ ] 在M运行 `npx wrangler deploy --dry-run --config services/reliable-drive-sync-worker/wrangler.production.toml`，预期目标断言失败；记录原始输出，排除语法/夹具原因。
- [ ] 最小实现：先核对远程权限与基线，备份必须可读恢复；暗部署配置全部新开关false，关闭旧按姓名发凭据入口再应用0008。测试环境完整链通过后，生产注册测试通过只给测试者的短期注册许可限制，而非普通用户UUID白名单（开户前无UUID）；未实现隔离许可则不开放生产测试。确认测试后移除测试限制并按批准策略启用公开限流注册。保留V2正常工作。推送两仓前fetch核对分叉，不强推；实测Git SHA及安装包一致。回退关新注册/配对不删数据，不恢复V1。
- [ ] 核心实现约束：
```text
reviewedAuthorization -> darkDeploy -> migration -> isolatedCanary -> publicEnable -> verifyRemoteSHA
```
- [ ] 同一命令全绿后运行本任务涉及模块的既有回归；POST只在真实证据齐全时审核。不把计划代码块当完整实现。
- [ ] 显式提交本任务文件，禁止add -A：
```powershell
# M仓库根
 git add services/reliable-drive-sync-worker/wrangler.production.toml docs/runbooks/device-release.md
 git commit -m "feat: t11 device binding deliverable"
# S仓库根
 git add docs/releases/device-release.md
 git commit -m "feat: t11 device binding deliverable"
```

### R2-T11-PRE

```yaml
review:
  id: "R2-T11-PRE"
  tasks: ["T11"]
  phase: "pre_implementation"
  after: ["R2-T10-POST"]
  blocks: ["T11"]
  level: "critical"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "云端迁移、公开开户与发行具有真实外部影响"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T11 Files与Interfaces及前置门结论"
    - "实际源码base SHA、测试设计、风险与失败窗口分析"
  checks:
    - "云端启用与GitHub交付的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "云端迁移、公开开户与发行具有真实外部影响，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T11相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T11-PRE，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T11的pre_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

### R2-T11-POST

```yaml
review:
  id: "R2-T11-POST"
  tasks: ["T11"]
  phase: "post_implementation"
  after: ["T11"]
  blocks: ["final_delivery"]
  level: "critical"
  status: "pending"
  model: "gpt-6-astra"
  reasoning_effort: "high"
  execution_mode: "manual_handoff"
  reason: "云端迁移、公开开户与发行具有真实外部影响"
  inputs:
    - "S/docs/superpowers/specs/2026-09-08-unified-submit-event-device-binding-design.md"
    - "T11 Files与Interfaces及前置门结论"
    - "base/head SHA差异、上述命令的实际版本/退出码/脱敏原始输出"
  checks:
    - "云端启用与GitHub交付的任务约束逐条满足，未沿用旧双工具/会话绑定"
    - "云端迁移、公开开户与发行具有真实外部影响，缺证据不能当通过"
  pass_when:
    - "本任务检查有充分证据且无安全、数据、规格或预算阻断；结论绑定输入版本"
  on_failure: "退回T11相关范围，修复后只复审变化；两轮同阻断交人工裁定"
  on_unavailable: "暂停R2-T11-POST，重验模型清单；无等能力替代则blocked_model_config"
```

提示词：审核T11的post_implementation，只读不改代码。先独立读原始输入再看实现者说明，按本任务逐条检查。返回pass、changes_required或insufficient_evidence；每问题给位置、证据、影响、blocking和验证方法。只审核该输入版本，不扩为全仓重复审。

## 覆盖与交接

B01=T01/T07；B02=T00/T05/T09；B03=T05；B04=T01/T05/T06；B05=T05；B06=T06/T07；B07=T00/T06；B08=T06；B09=T02/T03；B10=T03；B11=T00/T05/T08；B12=T02/T06；B13=T04/T09；B14=T07/T08/T09；B15=T07/T09；B16=T08/T11。

规格§1–6=T01/T05/T07；§7–8=T00/T05/T06；§9=T06/T07；§10=T02/T03/T05；§11=T02/T04/T06；§12=T08；§13=T09；§14=T10/T11。所有旧审核门无效，本文件21门均pending：9项critical前后审，2项deep与1项standard后审。没有light任务，不为了成本把认证/迁移降级。

下一步可在当前会话按executing-plans逐任务执行，或用户明确授权后选择分任务代理。第一步为T00 PRE及本机协调验证，不再探测可信聊天ID。不进入代码直到执行授权。

