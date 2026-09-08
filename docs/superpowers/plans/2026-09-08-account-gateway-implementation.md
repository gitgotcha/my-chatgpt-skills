# Account Gateway Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 只有用户另行选择并行代理后才使用 superpowers:subagent-driven-development。

**Goal:** 在 My Chatgpt Skills 中交付可自助注册、安全绑定、会话复用且严格隔离用户画像的账户网关。

**Architecture:** 新增 account_gateway 管理工具，submit_event 共用可信会话绑定；服务端每请求鉴权。本机安全存储管理设备秘密，每 UUID 独立 Outbox，云端 D1 原子处理注册和配对，不改变现有学习事实 reducer。

**Tech Stack:** Node.js 22.22.2 / 26.7.0、node:sqlite、PowerShell / Windows DPAPI、Cloudflare Workers / D1、现有 Miniflare 4.20260730.0、MCP stdio、Markdown skills。

**Spec:** [已批准设计规格](../specs/2026-09-08-account-gateway-design.md)。执行者必须完整阅读规格与本计划。

## Global Constraints

- 每个账户一个服务端生成的 UUID，允许同名账户拥有不同 UUID。
- 用户确认身份的交互只做一次，不代表取消服务端每请求鉴权。
- 不能假定一个 stdio 进程只服务一个聊天，也不能接受模型随意填写 threadId 作为可信会话证明。
- 设备凭据不进入模型上下文、MCP 参数或回包、日志、事件、Git、截图。
- 每入口验收上限 20 次，运行时总预算仍不超过 40，业务硬上限 50。
- 姓名规范化后 1–80 个 Unicode 标量、UTF-8 不超过 320 字节，拒绝控制字符；请求体不超过 4 KiB。
- 配对码至少 128 bit 随机熵，有效期 10 分钟，单次使用；兑换恢复窗口 24 小时。
- 新增迁移，不改写已应用的 0006/0007，保留全部既有 V2 数据。
- 第一版支持 Windows 桌面及 OS 安全存储；其他系统不能明文降级。
- 不实现公开用户目录、姓名找回、账户合并或删除；不开放旧管理员按姓名发凭据接口。
- 本文件仅计划。不得把下面的预期测试、预算估算、拟建文件表述成已实现证据。

## 0. 仓库、执行方式与门禁

S 表示技能仓库 C:/Users/27846/my-chatgpt-skills，当前分支 resume-knowledge-normalization；M 表示服务仓库 C:/Users/27846/my-chatgpt-mcp-v2，main。下文文件前缀 S/、M/ 为明确仓库映射，不是要创建的目录。

本机安装源 C:/Users/27846/plugins/my-chatgpt-skills 只作为技能差异输入，不能直接当成 Git 源。三份 M 仓库未跟踪审核文件保持原样。执行时按 using-git-worktrees 创建隔离工作区，不自动切换原分支。命令分别在指定仓库根执行，使用实际隔离工作区地址。

任务依赖：T00 → T01 → T02 → T03 → T04 → T05 → T06 → T07 → T08 → T09 → T10 → T11。

审核门：G0=T00 宿主可行性；G1=T01–T05 云端账户；G2=T06–T08 本机与网关；G3=T09–T10 插件与集成；G4=T11 发布。阻断只针对规格、安全、数据正确性与无法恢复的问题；新增非必要变异测试作为技术债，不无限延长门禁。

**重要：当前只有 T00 可以无条件开始。** 可信宿主作用域、安全界面及可移植启动的可行性尚无实测证明。其余任务为 G0 通过后的条件实施计划；若失败则回报并修订规格，不自行改成全局账户或把秘密传给模型。

## 1. 文件职责地图

| 目录 / 文件 | 职责 |
| --- | --- |
| M/shared/account-gateway-protocol.mjs | 封闭 DTO、规范化、错误码与常量 |
| M/services/reliable-drive-sync-worker/src/rds2/accounts/ | register.js、pairings.js、rate-limit.js、routes.js：原子账户流程与预算入口 |
| M/services/reliable-drive-sync-worker/migrations/0008_rds2_account_gateway.sql | 姓名非唯一迁移、账户管理表及事务守卫 |
| M/tools/reliable-drive-sync-mcp/gateway/ | host-scope.mjs、secure-store.mjs、session-store.mjs、account-client.mjs、account-outboxes.mjs、handler.mjs |
| M/tools/reliable-drive-sync-mcp/gateway/secure-dialog.ps1 | 只在用户操作时显示的本机确认/配对界面；秘密不输出到模型 |
| M/tools/reliable-drive-sync-mcp/stdio-bridge.mjs | 工具发现、可信上下文注入、账户分派；不塞入完整管理业务 |
| S/account-gateway/ | 公共账户技能及 references/runtime-contract.md |
| S/scripts/build-plugin.mjs、S/tests/account-gateway-package.test.mjs | 从已跟踪技能构建可安装产物与防路径硬编码测试 |
| S/plugin/.codex-plugin/plugin.json、S/plugin/.mcp.json | 可发布插件清单；启动机制经 G0 证明后写入 |
| M/tools/reliable-drive-sync-mcp/build-release.mjs | 打包固定版本的运行时与哈希清单，不包含本机数据 |

已有业务技能仍保持仓库根目录，不为包装无理由搬迁。构建产物复制到 dist/my-chatgpt-skills/skills；dist 不作为源码。插件含七个业务技能加 account-gateway 共八个技能，清单见 T09。

## T00：可信宿主、安全界面与基线验证（G0）

**Files:** 新建 M/tools/reliable-drive-sync-mcp/test/gateway-host-probe.test.mjs、M/docs/runbooks/account-gateway-host-evidence.md。仅使用合成数据探测。

**Interfaces:** 输出宿主证据：是否有模型不可伪造的 conversation scope、连接是否每会话独立、支持的安全输入与相对启动方法；不得输出真实凭据。T07 只消费经过此门验证的 transportContext。

- [ ] 记录两仓 HEAD/status，隔离工作区；运行 M `npm test` 保存基线；分别记录 Node 22.22.2、26.7.0 可用路径，不把版本说明当实跑结果。
- [ ] 在真实插件宿主启动两个聊天，各调用探针两次；探针只记录随机连接 nonce、请求序号和上下文字段名，不记录字段值、消息或环境变量。
- [ ] 写最小反例断言，证明客户端填写的 threadId 不可当可信来源：
  ```js
  assert.throws(() => resolveScope({ arguments: { threadId: 'A' } }),
    { code: 'trusted_scope_unavailable' });
  ```
  resolveScope 是探针内联测试函数；尚未生产接线。若不能从真实宿主获取可信隔离信息，记录失败并停止 T01–T11。
- [ ] 用合成码在本机安全窗口测试显示、输入、取消；只向父进程的私有管道发送结果，stdout 不含码。窗口关闭、管道中断返回 cancelled，不触网络。证明工具 transcript 仅有状态。
- [ ] 从另一测试目录启动插件，无开发者绝对路径；核实宿主插件根解析能力。安全界面、作用域或启动机制不能证明时停止，不能自行写猜测的宿主变量名。
- [ ] 运行 M `node --test tools/reliable-drive-sync-mcp/test/gateway-host-probe.test.mjs`。证据包含人工两聊天步骤与脱敏结果；只单测 Map 不能通过 G0。
- [ ] 显式提交两个文件：`git add tools/reliable-drive-sync-mcp/test/gateway-host-probe.test.mjs docs/runbooks/account-gateway-host-evidence.md`；`git commit -m "test: prove account gateway host isolation"`。

## T01：封闭协议与安全边界

**Files:** 新建 M/shared/account-gateway-protocol.mjs、M/services/reliable-drive-sync-worker/test/account-gateway-protocol.test.js。

**Interfaces:** `normalizeDisplayName(value)->string`；`validateAccountOperation(input)->{operation,params}`；`validateRegistration(input)->{requestId,displayName}`；导出 `ACCOUNT_PROTOCOL_VERSION=1`。设备秘密只通过 HTTP Authorization，配对码仅在运行时内部 HTTPS 请求体，不进入 MCP DTO。

公开 operation：current、find、register、bind、switch、unbind、transfer.create、transfer.redeem。find 增加可选 cursor（与规格分页要求一致），limit 固定 20；bind/switch/unbind 必须 expectedBindingRevision 为非负安全整数。current 和 transfer 操作 params 必须空对象。所有操作拒绝多余字段，尤其 threadId、token、userIdOverride、pairingCode。

- [ ] 写红灯：
  ```js
  assert.throws(() => validateAccountOperation({operation:'register',
    params:{displayName:'乔',token:'forbidden'}}), {code:'invalid_params'});
  assert.equal(normalizeDisplayName(' Ａ '), 'A');
  ```
- [ ] M `node --test services/reliable-drive-sync-worker/test/account-gateway-protocol.test.js`，先模块缺失红；补导出后必须有行为断言红。
- [ ] 实现规范化核心，并验证姓名长度、控制字符、孤立代理项、emoji、空白：
  ```js
  const name = value.normalize('NFKC').trim();
  const n = [...name].length;
  if (n < 1 || n > 80 || new TextEncoder().encode(name).length > 320 ||
      /[\p{Cc}\p{Cs}]/u.test(name)) throw Object.assign(new Error('invalid_display_name'),
      {code:'invalid_display_name'});
  ```
- [ ] 重跑同命令全绿；固定请求 UUID、操作返回错误码、所有数值范围测试。
- [ ] `git add shared/account-gateway-protocol.mjs services/reliable-drive-sync-worker/test/account-gateway-protocol.test.js`；`git commit -m "feat: freeze account gateway protocol"`。

## T02：同名账户迁移与事务底座

**Files:** 新建 M/services/reliable-drive-sync-worker/migrations/0008_rds2_account_gateway.sql、test/account-gateway-schema.test.js；修改同 Worker 的 test/support/rds2-d1.js，新增 `withAccountD1(callback)`，保留原 withD1 的旧迁移测试能力。

**Interfaces:** withAccountD1 在两种绑定应用至 0008。表字段冻结于本节；服务层只用这些字段，不临时扩充 SQL。

迁移次序：创建 rds2_users_next（与原 users 相同但 name_key 无 UNIQUE）→复制 users →创建 rds2_credentials_next（相同列，FK 指向 rds2_users_next）→复制 credentials →先删除旧 credentials 再旧 users →依次改名 next users/credentials →重建 credentials_user_idx 与 users_name_idx。全过程在 D1 migration 事务中，不使用 foreign_keys=OFF；其他 V2 表目前无指向 users 的 FK，执行前重新检索，出现新引用则停下修订迁移。不显式嵌套 BEGIN 于 Wrangler 迁移。

新增表完整列契约（所有时间为 UTC ISO 字符串，哈希 64 位小写 hex，ID UUID）：
  ```sql
  CREATE TABLE rds2_registration_intents (
    request_id TEXT PRIMARY KEY, proof_hash TEXT NOT NULL,
    input_hash TEXT NOT NULL, user_id TEXT NOT NULL REFERENCES rds2_users(user_id),
    created_at TEXT NOT NULL
  );
  CREATE TABLE rds2_pairing_tickets (
    code_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES rds2_users(user_id),
    source_credential_hash TEXT NOT NULL REFERENCES rds2_credentials(credential_hash),
    created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
    consumed_by TEXT UNIQUE, consumed_at TEXT,
    CHECK ((consumed_by IS NULL) = (consumed_at IS NULL))
  );
  CREATE TABLE rds2_pairing_redemptions (
    request_id TEXT PRIMARY KEY, code_hash TEXT NOT NULL UNIQUE,
    proof_hash TEXT NOT NULL, user_id TEXT NOT NULL REFERENCES rds2_users(user_id),
    created_at TEXT NOT NULL, recover_until TEXT NOT NULL
  );
  CREATE INDEX rds2_pairings_expiry ON rds2_pairing_tickets(expires_at);
  CREATE INDEX rds2_redemptions_expiry ON rds2_pairing_redemptions(recover_until);
  CREATE TABLE rds2_account_limits (
    bucket_key TEXT PRIMARY KEY, window_start INTEGER NOT NULL,
    attempts INTEGER NOT NULL CHECK(attempts >= 1), expires_at INTEGER NOT NULL
  );
  CREATE INDEX rds2_account_limits_expiry ON rds2_account_limits(expires_at);
  ```
为兑码添加 BEFORE INSERT redemption 守卫：必须存在 code_hash 对应 ticket、consumed_by=NEW.request_id、consumed_at=NEW.created_at 且 expires_at>NEW.created_at，并 JOIN 当前 active user 与 active source credential；否则 RAISE(ABORT,'pairing_invalid')。该守卫确保条件 UPDATE 零行时整批回滚，而非继续插凭据。SQL 守卫由 T04 并发测试覆盖。

- [ ] 写红灯：同名两 UUID 第二次 INSERT 原绑定失败；对原 users/credentials 填充多条合成记录，保存迁移前后逐字段排序值进行 deepEqual。
- [ ] M `node --test services/reliable-drive-sync-worker/test/account-gateway-schema.test.js`；确认 UNIQUE 红灯而非夹具错误。
- [ ] 实现迁移与新夹具；在真实 workerd 验证 DROP/RENAME 后 FK 指向 rds2_users，旧凭据可认证；非本任务表 hash/行数全部不变。
- [ ] 迁移中途失败整批回滚、同名成功、错误 FK 拒绝、pragma foreign_key_check 空结果全部绿。若真实 D1 不支持此迁移顺序，G1 阻断，不采用关闭 FK 绕过。
- [ ] 显式提交三个文件，消息 `feat: add account gateway storage migration`。

## T03：自助注册及响应丢失恢复

**Files:** 新建 M/services/reliable-drive-sync-worker/src/rds2/accounts/register.js、test/account-gateway-register.test.js。

**Interfaces:** `registerAccount({io,requestId,displayName,deviceSecret,now,uuid})->{userId,displayName,created}`。deviceSecret 为运行时生成 32 随机字节的 base64url 字符串，经 HTTPS Authorization 提交；哈希后落库。秘密不得出现在返回值。

- [ ] 写红灯：同 requestId/secret/name 连续两次 userId 相等；更换 secret 或 name 冲突；两个不同 requestId 的同名用户不同 UUID。
- [ ] M `node --test services/reliable-drive-sync-worker/test/account-gateway-register.test.js`，检查目标行为红。
- [ ] 实现一次按 request_id 点查；未命中生成服务端 UUID，以一次 io.db.batch 原子插 users、credentials、registration_intents。唯一冲突最多一次重查，不递归重试：
  ```js
  if (existing && (existing.proof_hash !== proofHash || existing.input_hash !== inputHash))
    throw Object.assign(new Error('registration_conflict'), {code:'registration_conflict'});
  ```
  匹配重放还必须核对账户 active 和凭据 active；失效不重新发凭据。inputHash 由规范化姓名的 canonical JSON 生成。异常用稳定 code，不透传 SQL。
- [ ] 并发同意图、同凭据不同意图、batch 中间失败、重查不可用、丢响应重试两绑定全绿；全路径最多一次冲突重查。
- [ ] 显式提交两个文件，消息 `feat: add idempotent self-service registration`。

## T04：配对创建、原子兑换与恢复

**Files:** 新建 M/services/reliable-drive-sync-worker/src/rds2/accounts/pairings.js、test/account-gateway-pairings.test.js。

**Interfaces:** `createPairing({io,principal,code,now})->{expiresAt}`；`redeemPairing({io,requestId,code,deviceSecret,now})->{userId,displayName}`。code 在来源设备生成并安全持久化，重复同码同来源创建返回原过期时间，不延长有效期；HTTP 响应无需返回原码。

- [ ] 写红灯：同时两个不同兑换请求 Promise.allSettled 后仅一个 fulfilled；凭据增加恰好 1；零行消费不能新增凭据。
- [ ] M `node --test services/reliable-drive-sync-worker/test/account-gateway-pairings.test.js`，先证明守卫测试有抓力。
- [ ] 创建：校验已鉴权 principal，插 ticket（32 随机字节 code，哈希保存，10 分钟到期）。兑换先查 redemption，命中必须校验 code_hash、proof_hash、24h 窗口及目标账户/凭据 active；只恢复结果。
- [ ] 新兑换一个 batch 顺序：条件 UPDATE ticket（未消费且未过期，来源账户和凭据 active）→ INSERT redemption SELECT ticket 用户（T02 守卫）→ INSERT credential SELECT redemption 用户。任何零来源行须被守卫/NOT NULL 拒绝，而非返回成功。全部 SELECT 绑定 requestId 和 codeHash，不接受 body.userId。
  ```sql
  UPDATE rds2_pairing_tickets SET consumed_by=?, consumed_at=?
  WHERE code_hash=? AND consumed_by IS NULL AND expires_at>?;
  ```
  此 SQL 为消费核心；来源有效性由同 batch INSERT 守卫再次检查。redemption 使用 INSERT VALUES 加标量子查询取 user_id，缺 ticket 时产生 NULL 并触发 NOT NULL，而不是零行 INSERT SELECT 跳过守卫；credential 同理，缺 redemption 必须整批失败。失败只做一次 redemption 重查，仍无法证明成功返回稳定 pairing_invalid 或临时 503。
- [ ] 已过期、已消费、错误码、来源撤销、目标撤销、各语句注入失败、丢响应恢复、恢复窗口边界全绿。恢复不能用新秘密绕过。
- [ ] 显式提交两个文件，消息 `feat: add atomic device pairing`。

## T05：HTTP 入口、限流与完整预算（G1）

**Files:** 新建 M/services/reliable-drive-sync-worker/src/rds2/accounts/rate-limit.js、accounts/routes.js、test/account-gateway-routes.test.js；修改 src/index.js、wrangler.toml、wrangler.production.toml。新开关 RDS2_ACCOUNT_GATEWAY_ENABLED=false，两配置均默认 false，旧 RDS2_INIT_ENABLED 保持 false。

**Interfaces:** `checkAccountRate({io,key,windowStart,expiresAt,max})->boolean`；`handleAccountRequest(request,env,context)->Response`。入口各自新建一次 createInvocationIo({db:env.DB,limit:20})，后续只传 io，不用裸 env.DB。

- [ ] 写红灯：第六次注册尝试 429；缺可信边缘 IP 或限流密钥返回 503；4 KiB+1 即 400 且零业务写；关闭开关 503。
- [ ] M `node --test services/reliable-drive-sync-worker/test/account-gateway-routes.test.js`。
- [ ] 限流用 D1 单语句 INSERT ON CONFLICT UPDATE attempts=attempts+1 RETURNING attempts，bucket_key=HMAC(服务端盐,操作+边缘IP或账户+固定窗口)。只信任平台边缘来源 IP；本地测试显式注入，生产不从任意客户端 X-Forwarded-For 取值。注册每小时 5，兑换每10分钟10，创建每账户每小时5。超限重试不会额外创建新桶；数据库故障 fail closed。
- [ ] 分块读取 request.body，累计超过 4096 bytes 即 cancel，不能先 request.text 再测大小。拒绝重定向、未知字段、错误 method；secret 从 Authorization 读取而非 MCP 入参。
- [ ] 完整 trace 估算：注册 rate1+lookup1+batch1+raceRecheck1+activeProof1≤5；创建 auth1+rate1+lookup1+insert1≤4；兑换 rate1+replay1+ticket1+batch1+raceRecheck1+activeProof1≤6。这是设计估算，实际超出估算要修正账目；任何路径超过20阻断，不能提额。
- [ ] 新建有界 cleanup 服务于 accounts/rate-limit.js 导出 `cleanupAccounts({io,now})`：每轮总计最多20条过期管理记录；选取后 batch 删除。未过恢复窗口 ticket 不删，已消费 ticket 与 redemption 成对删除；registration_intents 不清理。独立调用不塞进业务请求收尾。
- [ ] 全入口失败注入、鉴权、限流与日志脱敏测试绿；提交上述六文件，消息 `feat: expose budgeted account gateway routes`。

## T06：Windows 安全存储、对话框及云端客户端

**Files:** 新建 M/tools/reliable-drive-sync-mcp/gateway/secure-store.mjs、secure-dialog.ps1、account-client.mjs、test/gateway-secure-store.test.mjs、test/gateway-account-client.test.mjs。

**Interfaces:** `createSecureStore({root})->{read(ref),write(ref,value),remove(ref)}` 返回 Promise；`createAccountClient({baseUrl,fetchImpl,secureStore})->{register(intent),createPairing(intent),redeemPairing(intent),verify(credentialRef)}`。本机 intent 由运行时生成 UUID/秘密，模型不能传入 secret。

- [ ] 写红灯：安全存储失败 fetch 调用为0；云端成功而本机 metadata 写失败，重试网络请求 ID 与 Authorization 字节相同。
- [ ] M `node --test tools/reliable-drive-sync-mcp/test/gateway-secure-store.test.mjs tools/reliable-drive-sync-mcp/test/gateway-account-client.test.mjs`。
- [ ] 使用 Windows DPAPI 加密整个意图及秘密；同目录临时文件写完并 flush 后原子改名，损坏记录不覆盖。引用为 UUID 白名单，不允许路径穿越。秘密经私有 stdin/命名管道，不放进命令行参数、env 持久配置或 stdout。所有后台辅助进程 Hidden，仅用户主动操作的安全对话框显示。
- [ ] 实现 G0 已验证的安全输入界面：确认注册、配对显示/输入、取消；界面数据不截图、不自动写剪贴板。父子通信失败等同取消，绝不回退聊天输入。
- [ ] account-client HTTPS allowlist 固定服务端 origin，redirect:error；超时保留 intent。输出仅状态/UUID/姓名；注册完成先保存 credentialRef 与 metadata，最后才返回 bound。
- [ ] 错误、取消、磁盘满、原子改名失败、不同 OS 用户解密失败、进程中断恢复测试绿；显式提交五文件，消息 `feat: add secure local account enrollment`。

## T07：可信会话存储与切换

**Files:** 新建 M/tools/reliable-drive-sync-mcp/gateway/host-scope.mjs、session-store.mjs、handler.mjs、test/gateway-session.test.mjs。

**Interfaces:** `scopeFromTransport(transportContext)->scope`（G0 已证明的来源）；`createSessionStore()->{current(scope),bind(scope,expectedRevision,binding),unbind(scope,expectedRevision),assertCurrent(scope,revision)}`；`handleAccountOperation({scope,input,sessions,client,store,dialog})`。

- [ ] 写红灯：A/B 会话不互相改变；两次并发同 expectedRevision 切换只有一次成功；unbound→bind revision 为1，unbind 也单调递增，禁止归零 ABA。
- [ ] M `node --test tools/reliable-drive-sync-mcp/test/gateway-session.test.mjs`。
- [ ] 核心 CAS 在同进程串行段中执行，异步 verify 在 CAS 前完成：
  ```js
  if (current.bindingRevision !== expectedRevision)
    throw Object.assign(new Error('binding_changed'), {code:'binding_changed'});
  next.bindingRevision = current.bindingRevision + 1;
  ```
  多进程宿主必须由 G0 的独立 scope 保证无共享会话写；不能用进程全局 currentUser。
- [ ] find 只列 OS 用户安全存储元数据，分页 cursor 绑定本机清单版本和筛选条件，变更重读第一页；不得 HTTP 搜索全局姓名。current 不输出 credentialRef。
- [ ] bind/switch/register/transfer 通过本机界面授权，取消不改绑定；凭据失效转 reauth_required，重启丢弃 session 但保留安全存储。两技能复用一次确认测试绿。
- [ ] 显式提交四文件，消息 `feat: isolate account bindings by trusted session`。

## T08：业务工具接线与每账户 Outbox（G2）

**Files:** 新建 M/tools/reliable-drive-sync-mcp/gateway/account-outboxes.mjs、test/gateway-bridge.test.mjs、test/gateway-outbox-migration.test.mjs；修改 stdio-bridge.mjs、start-v2.ps1。按需修改 delivery-service-v2.mjs 的凭据失效停止路径并显式加入该次提交。

**Interfaces:** `createAccountOutboxes({root,credentialProvider})->{forUser(userId),close()}`；forUser 返回现有 delivery-service-v2 的 submit/flushDue/close。credentialProvider(userId) 永远只返回同 UUID 凭据，缺失抛 credential_invalid。

- [ ] 写红灯：A pending→切换B→flush A，网络仍携带A凭据；迟到A画像回包在B绑定下返回 binding_changed，不暴露A结果。
- [ ] M `node --test tools/reliable-drive-sync-mcp/test/gateway-bridge.test.mjs tools/reliable-drive-sync-mcp/test/gateway-outbox-migration.test.mjs`。
- [ ] tools/list 新增 account_gateway；submit_event 先从 transport 注入 scope，再查 binding。发请求捕获 revision，返回前 assertCurrent；个人操作 unbound 直接拒绝。旧 identity 字段只核对，不以它选择账户。
- [ ] 按 UUID 分库 root/accounts/UUID/outbox.sqlite；不直接修改进程 options.token。解绑不关掉有待投递事实的服务；凭据失效不忙循环，保留行待重新绑定同账户恢复。
- [ ] 迁移旧 outbox-v2.sqlite：先停旧服务取得排他访问并原生 backup；校验每行冻结 UUID，未知行全流程停止。保持原行状态、receipt、IDs、hash、时间，目标事务幂等插入并逐行比对；源库保留只读备份，不删除。迁移标记写成功后才让新服务恢复过期租约；不复制有效 sending 为 pending。
- [ ] 原 bridge、delivery、Outbox 测试与新测试全绿；真实双会话回归 G0；显式提交列出的文件，消息 `feat: route profile traffic through account gateway`。

## T09：技能统一与便携发行（G3 前半）

**Files（S）:** 新建 account-gateway/SKILL.md、account-gateway/references/runtime-contract.md、scripts/build-plugin.mjs、tests/account-gateway-package.test.mjs、plugin/.codex-plugin/plugin.json、plugin/.mcp.json。修改 AGENTS.md 和下列七目录 SKILL.md 及其存储引用：algorithm-learning、backend-project-learning、conducting-java-backend-mock-interviews、reviewing-java-backend-interviews、java-knowledge-based-on-resume-learn-skill、child-photography-editing、profile-aware-skill-creator。后两者从已验证本机源导入 Git，不覆盖其他五域原功能。

**Files（M）:** 新建 tools/reliable-drive-sync-mcp/build-release.mjs、test/gateway-release.test.mjs。

**Interfaces:** build-release 输出 runtime zip 与 SHA256；S 构建脚本消费固定版本包与匹配哈希，把原有技能复制进 dist/my-chatgpt-skills/skills 并包含 runtime。启动使用 G0 实测可用的插件根定位机制，不使用绝对开发路径，不在线追踪 main。

- [ ] 写失败包测试：启动配置含 C:/Users/27846 或未锁定 runtime 即失败；八技能清单缺一个即失败；引用不存在即失败。
  ```js
  assert.equal(manifest.name, 'my-chatgpt-skills');
  assert.equal(skillNames.length, 8);
  assert.ok(!JSON.stringify(mcp).includes('C:/Users/27846'));
  ```
- [ ] S `node --test tests/account-gateway-package.test.mjs`；M `node --test tools/reliable-drive-sync-mcp/test/gateway-release.test.mjs`。
- [ ] 新公共契约明确 current→未绑定才引导注册/绑定→submit_event。各技能加载公共契约且保留本来业务说明；删除现行按姓名自动注册/直接 Drive/旧回执承诺。画像技能生成器同步 schema、validator、真实生成测试，不只改 SKILL.md。
- [ ] 打包运行时采用 allowlist（shared、Bridge、gateway、所需本机模块），不打包测试秘密、Outbox、.wrangler、.git、个人配置。固定包哈希写入发布记录；本机缓存更新按 plugin-creator 的 cachebuster/reinstall 流程。
- [ ] 新 OS 用户合成安装验证：无个人绝对路径、无预设用户，确认界面取消零开户；新对话发现两个工具；普通答疑未登录仍可用。
- [ ] 两仓分别显式提交本任务实际变更路径，不 git add -A。消息 S `feat: integrate skills with account gateway`，M `build: package portable account gateway runtime`。

## T10：完整验收与预算证明（G3）

**Files:** 新建 M/services/reliable-drive-sync-worker/test/account-gateway-e2e.test.js、test/account-gateway-budget.test.js、M/docs/runbooks/account-gateway-acceptance.md；S 新建 tests/account-gateway-behavior.test.mjs。

**Interfaces:** 复用生产入口和双绑定 fixture，不测试另写的简化流程；证据按 A01–A16 编号记录命令、运行时、结果、失败与修复。

- [ ] 编写完整合成链：设备1注册A，设备2兑码绑定A，同名独立注册B；A上传算法事实，B不可读；设备1切换B，A旧队列仍投A；撤销A设备凭据后下一请求失败。
- [ ] 编写预算断言：
  ```js
  assert.ok(trace.used <= 20);
  assert.equal(trace.resetCount, 0);
  assert.equal(unwrappedIoCalls, 0);
  ```
  trace 收集生产同一预算器的 consume；失败调用也计数，不用手算代替。扫描账户模块的裸 fetch/env.DB 旁路并动态截获。
- [ ] M `node --test services/reliable-drive-sync-worker/test/account-gateway-e2e.test.js services/reliable-drive-sync-worker/test/account-gateway-budget.test.js`；S `node --test tests/account-gateway-behavior.test.mjs`。
- [ ] 在 Node22.22.2 与26.7.0分别运行 M `npm test`；运行技能既有测试与新技能验证器，保留业务能力，不让仅标题匹配代替行为测试。
- [ ] 手工真实宿主双聊天/安全窗口/新OS安装证据附入验收记录；未能自动化的项不得记作自动通过。对应矩阵：A01–04=T02–04/T10；A05–07=T00/T07/T08；A08=T03/T04/T10；A09=T05/T10；A10=T02/T10；A11=T06/T09；A12=T00/T09；A13=T08/T09；A14=T05/T06；A15=T10；A16=T11。
- [ ] 显式提交四份测试/验收文件到所属仓库，消息 `test: verify account gateway acceptance gates`。

## T11：暗部署、合成 canary 与 GitHub 发布（G4）

**Files:** 新建 M/docs/runbooks/account-gateway-release.md；修改发布记录及配置开关，S 记录 runtime/skill commit 与包哈希。只在实施获得发布授权后执行本任务远程步骤。

- [ ] 记录两仓分支与远端差异；禁止强推或默默覆盖本机安装源。显式核验上一门全部通过。
- [ ] 原生备份 D1 与本机 V2 库；先部署仍关闭注册的兼容版本，并禁用按姓名直接发凭据的旧脚本入口。确认原用户正常读写，再应用0008；不先开注册再修身份兼容。
- [ ] 在 M 执行 dry-run：`npx wrangler deploy --dry-run --config services/reliable-drive-sync-worker/wrangler.production.toml`；通过后部署同配置。禁止误用保持暗默认值的另一配置覆盖生产。
- [ ] 清理 cron 使用独立预算且每轮总计≤20管理记录，不能与既有恢复调用共享一个不计数的新预算器；如共用 scheduled invocation，总预算必须统一统筹并实测≤40。
- [ ] 测试环境先全链；生产仅临时显式测试范围开关，合成姓名/UUID不写真实用户画像。无法限定公开注册测试范围则不开放生产入口。
- [ ] 发布候选安装包并验证 hash，版本匹配后开启公开注册；默认限流验证后才开。失败先关注册/配对，不删除新账户或逆迁移姓名 UNIQUE。
- [ ] 显式提交发布证据；fetch 后检查分叉，冲突停止；按批准的合并流程推送 gitgotcha/my-chatgpt-skills 与 gitgotcha/my-chatgpt-mcp。核验远端 SHA，不能把本机缓存更新说成 GitHub 已更新。
- [ ] 最终报告真实注册/绑定/学习事实各阶段结果、版本、未完成项、备份位置和新会话提示；不在报告输出秘密或绑定码。

## 自检与交接

规格§1–4映射T01–04；§5映射T00/T07/T08；§6映射T01/T07/T08；§7–8映射T03/T04/T06；§9映射T08；§10映射T02/T05；§11映射T05/T10；§12映射T09；§13映射T10；§14映射T11。

本计划冻结了业务接口和事务方向，但不伪造宿主支持证据。G0 的结果决定能否实现已批准体验；未通过不启动下游。计划审核后可选同会话按 executing-plans 顺序执行，或用户明确授权后采用分任务代理方式；本轮不执行任何实现任务。
