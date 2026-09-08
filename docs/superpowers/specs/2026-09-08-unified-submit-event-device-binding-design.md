# 统一 submit_event 与本机账户绑定：开发规格 Revision 2

日期：2026-09-08

状态：用户已确认据此编写实施计划；尚未实施。替代 2026-09-08-account-gateway-design.md。现行计划为 ../plans/2026-09-08-unified-submit-event-device-binding-implementation.md；旧账户网关计划及审核门停用。

## 1. 目标与授权范围

My Chatgpt Skills 对 Agent 只公开一个 MCP 工具 submit_event，内部区分账户管理、只读查询、原有业务写入。账户默认绑定范围为同一台电脑的同一个 Windows 登录用户，首次绑定后跨聊天、进程与重启持久生效，除非用户明确切换或解绑。

账户网关技能只指导身份与授权操作，不读取或修改算法、面试、简历、项目学习等画像内容。统一工具入口不代表账户模块与业务数据耦合。

本轮只写规格，不改代码、凭据、数据、插件安装或云端配置。实施和发布按后续审核后的计划进行。

## 2. 替代旧设计的决定

| 旧设计 | 本版决定 |
| --- | --- |
| account_gateway 与 submit_event 两工具 | 仅 submit_event，账户操作为内部路由 |
| 每聊天单独绑定默认账户 | 同机同 Windows 用户共享持久默认账户 |
| 可信聊天 ID 是绑定前提 | 不依赖聊天 ID；依赖本机持久绑定版本与调用时一致性检查 |
| 重启丢弃绑定 | 重启保留绑定，在线操作仍服务端鉴权 |
| 技能固定清单与数量 | 发布前盘点当前 Git/插件源，保留更新后的技能，不按旧数量覆盖 |

不变：每账户一个 UUID；允许同名不同 UUID；姓名不是认证；自助注册需限流与幂等；已有账户通过本机凭据或安全配对绑定；所有业务请求服务端鉴权；V2 数据不迁移为其他用户。

## 3. 现状与实现差距

2026-09-08 只读核对：MCP 仓库基线 4f81009；stdio-bridge.mjs 已有单一 submit_event、V2 operation 查询和 schemaVersion=1.2 业务 envelope，但凭据仍来自进程级 options.token。账户表 name_key 仍唯一，管理员初始化仍按姓名复用账户，不能直接暴露为自助注册。

当前本机插件版本 1.0.0+codex.20260908132546，目录包含 algorithm-learning、child-photography-editing、conducting-java-backend-mock-interviews、java-knowledge-based-on-resume-learn-skill、profile-aware-skill-creator、review-model-routing、reviewing-java-backend-interviews、software-project-learning。目录存在不代表每项均被宿主发现；打包需同时核验清单与工具发现。执行前重新盘点，不恢复已替换的 backend-project-learning 名称，也不误删新增 review-model-routing。

## 4. 模块与信任边界

1. Agent：调用工具，利用回执中的姓名、UUID与绑定上下文理解当前对象；不能凭上下文指定权限。
2. submit_event 分发器：严格校验输入形状，按封闭路由选择账户、查询或写模块。
3. 账户模块：只访问本机绑定/凭据及服务端账户、设备凭据、注册和配对记录；不导入业务 reducer，不理解题目与评分。
4. 业务传输模块：取得已授权 principal 后读取画像或持久化事件；自行维护业务 Outbox、回执与缓存。
5. Worker：根据凭据查询账户有效性并派生 userId；body 中身份字段只作一致性校验。

账户模块对业务提供 authorizeCurrent(expectedBinding) 与内部凭据访问能力，不返回秘密给 Agent。业务模块不直接读 Windows 凭据文件。普通不读写个人数据的讲解、规划、编辑不强制登录；授权限制的是个人数据操作，不宣称技能 Markdown 能在宿主层禁止所有技能加载。

## 5. 单工具输入契约

保留现有两种顶层形状，互斥匹配；混合 operation 与业务 envelope 必须拒绝，不能靠字段优先级猜路由。

### 5.1 账户与查询

使用 storageVersion=2、operation、params。个人查询另带顶层 bindingContext；这不是凭据，而是防止旧上下文被悄悄切换的匹配条件。

```json
{"storageVersion":2,"operation":"account.current","params":{}}
```

账户 current 返回可见信息：state、userId、displayName、bindingContext。bindingContext 含 installationId（随机本机安装标识）、bindingEpoch（随机绑定代标识）、bindingRevision（单调整数）、userId；均非秘密。state 为 authenticated、unbound、reauth_required 或 verification_unavailable。只有完成服务器凭据校验才返回 authenticated；离线不得把本机记录称为已认证。错误状态下不签发可用授权。

```json
{
  "storageVersion":2,
  "operation":"projection.read",
  "params":{"namespace":"algorithm","projectionName":"learning","limit":20},
  "bindingContext":{
    "installationId":"回执中的安装标识",
    "bindingEpoch":"回执中的绑定代标识",
    "bindingRevision":1,
    "userId":"回执中的UUID"
  }
}
```

这些字符串仅为字段说明，执行请求必须使用实际回执。bindingContext 由运行时核对，不能用于按 UUID 寻找另一人的凭据。

### 5.2 业务写入

保留 schemaVersion="1.2"、namespace、eventType、identity、payload、requestId 的既有契约，新增顶层 bindingContext。分发器验证后剥离该上下文字段，再传给原业务校验器；它不进入冻结业务 envelope、业务 hash 或云端事件。既有业务字节限额保持不变。

没有 bindingContext 的个人读写返回 binding_context_required，零业务 IO；Agent 调用 account.current 后再发请求。旧客户端不自动补当前账户，避免把旧 A 内容静默写给 B。已冻结 Outbox 后台重试不属于 Agent 新调用，按§9处理。

## 6. 账户操作清单

| operation | 参数与条件 | 结果 |
| --- | --- | --- |
| account.current | 空 params；不要求旧绑定上下文 | 核验本机默认账户；返回当前状态和非秘密身份 |
| account.find | 可选 displayName、cursor；固定每页≤20 | 仅当前 Windows 用户本机已合法绑定账户，不查全站姓名 |
| account.register | displayName、用于识别本次管理意图的 requestId | 安全界面确认后创建新账户；无默认账户才尝试首次绑定 |
| account.bind | accountHandle、expectedBinding；仅当前未绑定可用 | 核验本机已有凭据后原子绑定 |
| account.switch | accountHandle、expectedBinding | 安全界面明确确认机器默认账户切换，影响本 Windows 用户全部聊天 |
| account.unbind | expectedBinding | 确认后解除本机默认绑定，不删除云端数据或设备凭据 |
| account.transfer.create | 当前 bindingContext | 已认证设备安全显示配对码，MCP 不返回码 |
| account.transfer.redeem | requestId | 安全界面输入码；创建新设备绑定记录，无默认账户才尝试首次绑定 |

expectedBinding 是 current 返回的本机版本描述；unbound 状态也有安装标识、epoch和revision用于 CAS。管理 requestId 是非秘密幂等标识，运行时先持久化意图；模型重复调用相同 requestId 不应重新开户或重新申请秘密。

注册或配对完成时若其他进程已绑定账户，不覆盖新默认账户，返回 account_created_not_selected 或 account_bound_not_selected。已有默认账户时注册新账户也不自动切换。用户后续必须明确 account.switch。

公开 capabilities 可无个人凭据返回版本和支持能力；禁止返回账户清单。user.resolve 若保留只作为受鉴权的一致性核对兼容操作，不新增公开用户搜索。

## 7. 本机持久绑定与跨进程并发

隔离范围为 Windows 当前登录用户安全存储目录，不按设备硬件指纹自动识别人，也不让同机另一个 Windows 用户解密或继承凭据。同一个 OS 用户下的多个聊天共享默认账户是明确产品行为，不承诺这些聊天之间互为安全隔离租户。

持久数据分为：加密设备秘密、账户元数据、本机默认绑定记录。绑定记录含 installationId、bindingEpoch、bindingRevision、userId/空、credentialRef；不保存题目、画像、会话消息。installationId 首次初始化生成，重装保留数据时不变；数据重置时重新生成。每次绑定变化生成新 epoch 且 revision 递增，防 A→B→A 或备份恢复造成旧上下文误通过。

采用跨进程可证明的持久 CAS，不能仅进程 Map 或文件覆盖；预验证目标凭据，进入本机短事务核对 expectedBinding，再提交新绑定。验证期间其他进程切换则拒绝 binding_changed，不抢占新选择。不得跨网络持有 SQLite 写事务。

每次个人操作读取本机权威绑定并核对完整 bindingContext，不能只靠内存缓存。切换后不需要重启其他进程才能生效。凭据失效保留选中账户，进入 reauth_required；网络故障只报告核验不可用，不自动解绑、注册或换人。

默认状态跨新聊天和重启保持；新聊天首次个人操作通过 account.current 取得上下文，不向用户反复问姓名。已经取得的上下文可由 Agent 复用，但不作为授权本身。

## 8. 账户切换与迟到结果

运行时将检查通过时的 principal、bindingContext 捕获为不可变请求上下文，后续网络调用只能使用该账户凭据。

- 请求开始前发现绑定变化：binding_changed，零业务写，Agent 重新查询 current；不能自动换身份重试旧内容。
- 查询进行中发生切换：请求仍属于原账户；回包前检查版本，旧结果不展示、不放入新账户缓存。
- 新写入的本地接纳与绑定切换必须有明确线性化顺序：在共享本机锁/事务协调下复核绑定并完成 Outbox 接纳，或实现等效的可验证协议。不能在两个无协调数据库之间先查后写。
- 写入已被 Outbox 接纳后发生切换：事件永久属于原账户。回执明确 eventOwnerUserId 与 bindingChanged=true；不报告“零写入失败”，不自动为新账户再造事件。Agent 只说明原账户事件状态，不在新上下文显示原画像内容。

不能从已有聊天中物理删除模型已看过的旧画像。因此切换后技能不得将旧证据自动归给新账户；用户需要明确指定新账户的新事实。系统保证身份标签、传输和数据隔离，不保证识别任意自然语言内容究竟属于谁。

## 9. D1 正确归属与业务工作模式

服务端每个个人请求验证凭据及账户状态，从凭据确定 userId。请求填写其他 UUID 或姓名不一致时拒绝，不能以请求内容重绑定。

只读查询走现有 D1 物化画像/状态接口，不创建 Outbox 或业务事件。业务写仍按原流程：校验→本机可靠 Outbox→D1 原子接收及幂等→Queue 投影→Drive 归档。网关不读取或构造这些业务数据。

Outbox 冻结原账户 UUID、原始业务 envelope 与幂等标识；后台投递按冻结账户获取同账户有效凭据，绝不按机器“当前用户”选择。当前默认账户切换或解绑不转移旧事件。原账户凭据不可用时停在可恢复状态，不忙循环或改投新账户。

保留原有回执分层：pending仅本机，d1_committed仅云端账本，projected与archived分别核验。身份确认成功不是业务提交成功。云端接收丢响应后使用原IDs及内容重试，不创建第二份事实。

## 10. 注册与新设备绑定安全

每账户一个服务端生成 UUID，允许同名；姓名规范化 NFKC、trim，1–80 Unicode标量且UTF-8≤320字节，拒绝控制字符和孤立代理项。姓名不查询他人、不提供找回。

自助注册尚无用户凭据，走专用校验、限流和幂等模块，不复用管理员按姓名绑定逻辑。运行时先安全持久化requestId及至少256bit设备秘密；服务端原子写账户、秘密哈希和注册幂等记录。相同意图及秘密恢复相同UUID，不同秘密或姓名冲突；不同意图同名创建不同UUID。密钥不进入MCP、日志、Git或业务事件。

安全配对码至少128bit随机熵，有效10分钟，来源为已认证设备。通过本机安全界面展示/输入，不进入聊天、工具参数或截图。目标设备先持久化新设备秘密与兑换意图，原子消费码并新增凭据。同一兑换意图、同一目标秘密可在成功后24小时恢复结果；其他兑换或过期码失败。来源账户/凭据无效时拒绝新兑换。

无已认证设备且全部凭据丢失，第一版不支持按姓名自动找回。账户管理意图独立于学习Outbox，注册不生成学习事件。

## 11. 存储迁移、预算及失败策略

新增迁移移除姓名唯一约束、创建注册/配对幂等记录；保留既有UUID、凭据、V2事件、投影和归档。旧管理员按姓名发凭据脚本退出使用，不在多同名条件下恢复。Windows旧V2绑定只能通过已有凭据核验后导入，不能按文件中的姓名重建账号。未知归属队列停止迁移并保留备份。

单一MCP工具不要求一个HTTP地址，也不要求一次调用包办整个学习流程。内部账户路由、/v2/query、/v2/events可独立；每个Worker invocation独立计数且只有一个预算器。账户入口≤20，现有运行时总上限≤40，业务硬上限50；失败、鉴权、限流、重定向均计数。单次MCP串行多请求不得用来规避无限工作量，应有封闭分流和有界重试。

账户请求≤4KiB，流式读取超限即拒绝；业务写保持既有256KiB等原有分层限制，不套用账户小包限额。注册每IP每小时5次、兑换每IP每10分钟10次、配对创建每账户每小时5次；限流设施不可用失败关闭。管理数据清理每轮总计≤20条，不能误清未过恢复窗口的记录。

稳定错误包括 unbound、binding_context_required、binding_changed、credential_invalid、verification_unavailable、registration_conflict、pairing_invalid、rate_limited、secure_store_unavailable。不透传SQL、凭据或其他用户信息。查询/鉴权失败不自动写数据；管理员权限不分发给安装用户。

## 12. 技能接入与可移植发布

账户网关技能只负责指导调用 submit_event 的 account.* 操作。它不依赖领域名、业务payload schema、画像表结构或reducer，不接收整份画像作为身份校验输入。统一运行时以操作注册表分发，各领域继续维护自身契约。

所有个人画像技能使用 current 回执取得 bindingContext，携带它调用原查询/写入操作。普通无个人数据功能可继续使用。review-model-routing 等不需要用户画像的技能不增加登录依赖。发布前按当前Git与安装源盘点，不固定旧技能名称或数量；新生成的画像技能引用同一授权契约。

安装包只公开 submit_event；不新增 account_gateway 工具。运行时固定版本与包hash，不引用个人Windows路径或浮动main。第一版Windows安全存储，不支持平台明确拒绝持久授权，不明文降级。升级保留已验证绑定；升级工具schema后新会话加载，旧客户端无bindingContext的个人操作稳定拒绝。

GitHub交付分别位于my-chatgpt-skills（技能、包装、契约）与my-chatgpt-mcp（运行时、Worker），记录实际commit及包hash。只改本机缓存不算源码交付。

## 13. 验收门

| ID | 必须证明 |
| --- | --- |
| B01 | 工具发现只有submit_event，三类请求互斥分流，混合字段拒绝 |
| B02 | 同机同Windows用户跨聊天/进程/重启复用首绑；不同Windows用户隔离 |
| B03 | current在线核验返回正确UUID，离线/撤销不谎报authenticated |
| B04 | 旧bindingContext、A→B→A、并发切换均不能静默变更请求归属 |
| B05 | 切换失败原绑定不变；注册/兑码并发完成不覆盖已有选择 |
| B06 | 迟到查询不显示旧画像；已接纳写回执指明原账户，不触发新账户重复提交 |
| B07 | 本地写接纳与切换有跨进程线性化证据，不是进程Map或两个库先查后写 |
| B08 | A旧Outbox在默认B时只投A；凭据失效保留行并停止忙重试 |
| B09 | 同名不同UUID；注册并发/丢响应只恢复原意图；姓名不能冒领 |
| B10 | 兑码单次消费、时效、来源撤销、恢复窗口与目标秘密证明正确 |
| B11 | 密钥/码不进MCP、日志、Git；安全存储失败零网络注册 |
| B12 | D1双绑定迁移/事务守恒，旧V2记录及凭据全部保留 |
| B13 | 生产入口完整预算≤配额；限流失败关闭；无直接IO旁路 |
| B14 | 账户模块不导入业务reducer或查询画像；领域测试使用模拟授权接口可独立运行 |
| B15 | 四域原业务回归、分页一致性、幂等及归档不变；个人读无事件写 |
| B16 | 干净Windows安装无个人路径，新用户可安全注册绑定，旧客户端明确失败而非猜身份 |

本版不再要求可信聊天ID作为发布阻断门，改为真实多进程持久绑定、Windows用户隔离、安全输入和写接纳/切换原子协调验证。身份安全验证不能因取消聊天ID门而取消。

## 14. 实施计划与发布约束

旧计划中的独立工具、sessionScope、每会话绑定、固定八技能及对应审核输入全部失效。重编计划时保留注册、配对、D1原子性、预算和数据守恒要求；审核门重新绑定新规格与版本，不能沿用旧pass结论。本轮不派发审核模型。

实施顺序：验证Windows安全存储与跨进程协调→冻结统一输入与绑定上下文→账户事务→本机绑定及原Outbox接线→技能解耦与包发布→双运行时/双绑定集成→暗部署与隔离canary→正式发布。

发布前备份，注册开关默认关闭；先部署兼容身份逻辑再迁移再启用。只用合成账户验证，不写真实用户学习事实。回退关闭新注册/配对，保留数据；不恢复按姓名接管、不逆迁移姓名唯一约束。生产操作与Git推送在后续执行任务中核对授权，不在本轮进行。

## 15. 本轮交接

本规格为下一版实施计划的唯一业务依据。用户审核后再重编计划及模型审核分工；现有旧规格/计划保留作历史，带明显停用标记。文档完成不表示账户网关或机器绑定功能已上线。
