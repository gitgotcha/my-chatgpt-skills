> **已被 v3 取代，历史参考，不执行本文件任务。** 用户选择固定 domain＋稳定项目 ID，入口名为 `project-12306`，前缀 `project-`。以下旧斜杠分域、Creator1.1、projectContractVersion2及迁移方案撤销。请改读 [2026-10-25-project-learning-project-alias-design.md](2026-10-25-project-learning-project-alias-design.md)。

# 项目学习设计 v2：按 project/12306 分域

日期：2026-10-25（Asia/Shanghai）。状态：设计与实施交接，尚未实现或部署本次分域功能。

配套：[执行计划](../plans/2026-10-25-project-learning-project-domain-plan.md)、[验收与完整分域示例](2026-10-25-project-learning-project-domain-acceptance.md)。延续用户指定的“DeepSeek实施、用户提交、Codex复核”。

## 1. 用户要看到的结果

项目学习使用同一个可复用 Skill，各项目分别保存上下文：

| 学习项目 | 实际业务 domain | 教学提纲读取目标 |
|---|---|---|
| 12306 | `project/12306` | namespace=`profile`，projectionName=`project/12306` |
| pig-rpc | `project/pig-rpc` | namespace=`profile`，projectionName=`project/pig-rpc` |
| RAgent | `project/ragent`（示例，运行时需确认绑定） | namespace=`profile`，projectionName=`project/ragent` |

这里采用用户给出的**真实 domain 字符串**，不在界面展示斜杠、后台却偷偷存成 `backend-project-learning` 或 `project-12306`。domain 是 JSON 中的业务路由值，不是 namespace、文件系统路径或 Drive 文件夹。namespace仍是profile/interview等现有协议值。

保留已认可的教学闭环：原创场景代入与适当幽默 → 可见时序图 → 核验源码及详细注释 → 状态、反例与责任边界 → 口述答案 → 底部一道追问。真实用户回答前停下来；补答不覆盖首答；仅合成样例不得写成个人能力。

正式问答继续接入面试证据。用户说“只从project/12306考我”，就读取该业务域绑定的项目UUID，再读取相同项目的面试快照，换条件追问和新增作答。次日开场先回顾昨日框架，**回顾的问答、提示、反馈、评价完全不落库**。只另外记录实际讲授过的中性提纲。

## 2. 本次核验与依据

维护源 S=`C:\Users\27846\my-chatgpt-skills`；实际运行时 R=`C:\Users\27846\my-chatgpt-mcp-v2`。

| 核验项 | 2026-10-25事实 | 对本次设计的影响 |
|---|---|---|
| 最新创造器 | S/profile-aware-skill-creator/SKILL.md及新references/rds-v2-interface-and-file-format.md已读取，均含本地未提交优化 | 采用当前工作树内容，不以旧缓存代替 |
| 新增规范 | namespace与domain分开；凭据身份；唯一submit_event；结构化JSON；不支持任意文件/base64上传；分阶段回执 | 新设计逐项遵循 |
| Creator静态schema | schemaVersion1.0，domain限2—64字符的小写kebab-case；validator另有SAFE_ID检查 | 不能仅改项目学习文案；需要有限的模板合同扩展 |
| Worker校验 | R/src实际位置为services/reliable-drive-sync-worker/src/generic-profile-contract.js；同样不接受斜杠 | 要改实际V2纯校验器及其调用链 |
| 上一版实现 | 两仓库工作树已有项目学习、项目问答、查询过滤和投影代码，包含0008项目/attempt身份表 | 本次在其上增量升级，不重新创建整套引擎 |
| 本地与在线 | 本地query.js已有interviewProjectSnapshots声明；在线capabilities仍只有domains/storageVersion/writes，未返回该feature | 本地文件存在不代表已上线；设计不宣称前一版已通过验收 |
| Git基线 | S HEAD=`7c588e4fd2e0e35ccc5a6f2fa8e527806af0deae`；R HEAD=`720916e4c336148cb43bf53051bc01007df1c5a7`；两者均dirty | 实施以HEAD+现有工作树哈希清单为基线，保护已有改动 |

本轮只做设计、材料核验与只读capabilities；没有解析个人身份、读取私人画像或写入学习事件。实际代码、未提交状态、在线能力分别记录在交接包source-evidence.json。

## 3. 按最新Creator记录的创作决定

1. **目标目录**：继续使用S/software-project-learning；已经存在，原地增量更新，不新建project/12306技能文件夹。
2. **画像分支**：是。此前已明确要求跨会话提纲、正式作答与面试联动，不重复问是否保存。
3. **domain**：运行时解析为project/<projectSlug>，12306明确为project/12306。本次新增有限的项目域例外，保留原平铺域合同。
4. **sourceSkill**：software-project-learning，不能改成project/12306。
5. **维度**：通用画像仍只有learning-outline；subjectKey保持<projectId>:<unitId>，以兼容既有提纲定位。正式问答沿用专用interview合同，不复制成另一份generic能力分数。
6. **可观察证据**：提纲只记录本轮实际讲过的框架，outcome仅observed；sourceRef必须能追溯当次讲授消息。看过答案、提示补答、回顾和合成数据都不算独立掌握。
7. **三个画像工件**：更新现有references/profile-contract.md、schemas/profile-capability.json、tests/test_profile_contract.py；SKILL.md最小链接。已有项目证据合同与纯构造器是当前业务资源，继续复用。
8. **校验**：先扩展Creator模板schema和validator，再运行profile模式与目标技能测试。静态能力文件通过不能代替在线capabilities。

本次技术选择由设计提出，供用户审阅；原始教学偏好、分域格式和交接方式来自用户。不是再次询问已经确定的偏好。

## 4. 方案取舍

考察三种实现：只改显示名称（不能满足真实domain要求）；把新域写成project-12306（偏离用户格式）；**有限支持project/<slug>并绑定既有UUID**（采用）。

不开放任意多级路径，不把所有SAFE_ID都放宽，也不把project变成新的namespace。静态技能使用一个受限模板，运行时解析成具体值；RDS仍只接收确定的domain字符串。这需要Creator和V2协同升级，但可保留旧事件、原项目UUID和既有快照。

## 5. 域命名与身份绑定

### 5.1 唯一接受的新增形式

新项目域正则：`^project/[a-z0-9](?:[a-z0-9-]{0,54}[a-z0-9])?$`。

- 前缀project/恰好8字符，slug为1—56字符，整个domain最多64字符。
- slug只含小写ASCII字母、数字和内部连字符；单字符slug允许，例如project/a。
- 必须匹配完整字符串，拒绝首尾空白和末尾换行；不能只依赖JavaScript中可在末尾换行前匹配的`$`。
- 拒绝空slug、首尾连字符、大小写变体、空白、反斜杠、额外斜杠、点段、百分号编码和Unicode混淆形式；不先URL解码或静默小写化再存。
- project/12306、project/pig-rpc有效；project、Project/12306、project/../12306、project/12306/a、project/%31%32不属于本例外。
- 原有平铺domain的正则、保留字和历史语义不变。dimensionKey与sourceSkill仍使用原safe identifier，不能因此包含斜杠。

域路径不用于拼接远端文件名或目录。Worker继续以既有artifactId、规范JSON和归档校验机制工作，技能不获取Drive ID、不上传源码或录音。

### 5.2 domain与UUID各负责什么

projectDomain是可读、稳定的业务路由；projectId是既有项目UUID，用来关联面试attempt与快照。保持同一用户内一对一绑定：一个UUID只有一个projectDomain，同一projectDomain只绑定一个UUID。同名项目属于不同用户时互不关联。

复用0008创建的rds2_interview_projects身份表，不重命名也不复制一张竞争的项目表。新增project_domain可空列、domain_bound_event_id可空列；对(user_id,project_domain)建非空唯一索引。旧记录保持NULL，禁止按display_name或仓库路径自动填slug。

绑定既可由首条真实教学提纲事件建立，也可由首条正式session建立：所有projectId、basis和domain冲突检查、身份映射、事件、receipt与任务在同一个接纳事务中完成。教学先于作答时，也能跨会话找回项目UUID。后续相同UUID的basis须匹配；同一basis不得换UUID；已绑定domain不得静默改名。

已存在旧UUID时，先通过凭据范围内的项目目录匹配其已确认basis/用户选择，再绑定project/12306。不要再造一个UUID把历史分叉。仓库显示名、路径或commit变化不会触发新项目。新域也不是事实上的用户身份，不能由它选择其它账户。

**旧提纲存在、目录为空的恢复**：0008只在正式session中建项目，因此不能把空目录解释成全新项目。目录未找到时，先只读旧profile/backend-project-learning提纲，从严格UUID:unitId的subjectKey解析候选UUID，展示其原sourceRef、讲授日期和最小框架片段，让用户确认它是否属于本项目；不能用相似名称自动确认。候选尚未确认，或旧投影读取失败/构建中时，只做当前会话教学，不生成竞争UUID、不远端保存。确认后由首条真实新事件用原UUID建立目录和domain绑定；旧提纲不重发。只有完整检查无可确认候选且用户确认是新项目时才创建新UUID。

并发首次绑定由唯一约束决定；失败方返回project_domain_conflict或project_identity_conflict。原包保留为blocked，不自动换ID掩盖冲突。用户明确选择已有项目后，可按纠正后的新意图构造新包并在本地交接记录说明与原失败请求的关系；不修改已接纳事件。

domain重命名、项目合并和删除不是本次功能。更换显示名称不应改变domain；将来确需别名时另设明确迁移合同。

## 6. 版本与具体DTO

以下是**待实施合同**。当前在线未声明支持，不得直接发送示例。

### 6.1 静态profile-capability.json采用1.1项目模板

旧profile-capability.schema.json（1.0）保持原样。新增profile-capability-v1.1.schema.json；validator按schemaVersion选择schema，并同步其手写字段检查。未知版本拒绝。不用把oneOf添加到schema却忘了实现当前自制schema解释器。

1.1仍保留sourceSkill、dimensions、evidencePolicy、runtime、portability。以domainTemplate和domainParameters代替1.0的domain，二者不能混写。模板只能是常量project/{projectSlug}；不允许任意前缀、表达式或路径模板。

```json
{
  "schemaVersion":"1.1",
  "domainTemplate":"project/{projectSlug}",
  "domainParameters":{
    "projectSlug":{
      "pattern":"^[a-z0-9](?:[a-z0-9-]{0,54}[a-z0-9])?$",
      "minLength":1,
      "maxLength":56,
      "resolveFrom":"confirmed_project_binding"
    }
  },
  "sourceSkill":"software-project-learning"
}
```

上面只展示差异字段，不是完整静态工件。runtime继续既有操作字段，并在1.1增加projectDirectoryReadEvent=project.list；identityRegisterEvent沿用旧静态admin_only策略标记，但实际技能仍不得调用注册或切换账户。只有凭据绑定身份核对可用于运行。

完整静态工件需要测试：解析12306得到project/12306；解析pig-rpc得到project/pig-rpc；不能把模板本身当wire domain；两个项目切换不能沿用上一个项目的缓存上下文。

### 6.2 在线feature与只读目录

保留capabilities.domains的namespace语义，新增：

```json
{"features":{"projectDomainRouting":{"version":1,"domainTemplate":"project/{projectSlug}","projectContractVersion":2,"directoryRead":true}}}
```

通过新增RDS2_PROJECT_DOMAIN_ENABLED开关控制，默认false。代码、增量迁移、查询和测试齐备且配置启用后才声明feature；服务端也按该开关拒绝新域写入，不能只依赖客户端。关闭入口不阻止此前已接纳事件继续归约、归档和通过原ID查状态。正式项目问答仍同时要求既有interviewProjectSnapshots能力。

新增原生只读操作project.list，经同一个submit_event调用：

```json
{"storageVersion":2,"operation":"project.list","params":{"limit":20,"projectDomain":"project/12306"}}
```

params仅允许limit、cursor、projectDomain；后二者可选。返回revision、projects、nextCursor。每项只有projectId、projectDomain（旧项目可null）、displayName、basis四项最小元数据，不返回答案或他人信息。按凭据user_id查身份映射；projectDomain精确过滤；projectId升序；limit≤50，响应≤256KiB。

目录支持尚无作答、只有教学提纲的项目。无筛选时也列出domain尚未绑定的旧项目，供用户按已确认basis选择历史UUID；不能把null域当成project/unknown。

新增rds2_project_directory_heads(user_id主键,revision整数)。接纳事务中只要项目目录项新建、补绑domain或可见元数据变化就增加revision，包含旧v1事件新建项目的路径。cursor绑定user、operation、projectDomain筛选、revision、lastProjectId、过期时间；15分钟过期。目录改变返回directory_changed/409并从头重读。不同投影的revision没有全局可比性。

### 6.3 提纲写入：namespace=profile、payload.domain=project/12306

内部generic event保持schemaVersion1.0及既有字段，identity只在外层。新增payload.projectRef（仅project/*域允许并必填），严格四字段：projectId、projectDomain、displayName、basis；basis仍为kind/key。projectRef.projectDomain须与payload.domain完全一致。

```json
{
  "schemaVersion":"1.2",
  "namespace":"profile",
  "eventType":"profile.evidence.recorded",
  "identity":{"userId":"22222222-2222-4222-8222-222222222222","username":"隔离演示学员"},
  "payload":{
    "domain":"project/12306",
    "projectRef":{
      "projectId":"11111111-1111-4111-8111-111111111111",
      "projectDomain":"project/12306",
      "displayName":"12306",
      "basis":{"kind":"source_learning","key":"confirmed-source:train-12306"}
    },
    "event":{
      "schemaVersion":"1.0",
      "eventId":"33333333-3333-4333-8333-333333333333",
      "eventKey":"fixture:outline:12306:unit-query:1",
      "observedAt":"2026-10-25T01:00:00Z",
      "sourceSkill":"software-project-learning",
      "action":"observe",
      "observations":[{
        "dimensionKey":"learning-outline",
        "subjectKey":"11111111-1111-4111-8111-111111111111:unit-query",
        "outcome":"observed",
        "evidence":"已讲授余票展示：请求校验、候选车次、价格与余票、缺失回源和返回Map责任。",
        "confidence":"high",
        "sourceRef":"learning-unit:unit-query:fixture-conversation:fixture-message"
      }]
    }
  },
  "requestId":"44444444-4444-4444-8444-444444444444"
}
```

全部身份/证据/ID均为合成，禁止写真实账号。projectRef不是文件上传口，也不属于内部generic event；未知字段、不同用户projectId引用、绑定不一致、subjectKey项目UUID不匹配、非中性提纲均拒绝。旧平铺域无projectRef的事件继续原合同，不能给所有generic skill强塞项目字段。

project/*域的教学事件只含1—20个learning-outline观察项，每项evidence为8—800字符、outcome=observed、confidence=high、subjectKey归同一projectRef，sourceRef可定位实际讲授消息。结构校验不能证明文字真的发生过，技能仍须从真实对话取证。保持原generic事件大小与投影预算，不用上传源码/附件补足证据。

读取仍是现有projection.read：namespace=profile，projectionName=project/12306，limit=20。保持分页revision；按既有cursor_scope_mismatch保护不同domain。不要构造namespace=project/12306，也不把project/12306写进interview题目的知识领域domain字段。

### 6.4 正式问答：projectContractVersion=2增加项目路由元数据

在既有Question.projectEvidence.project对象新增唯一字段projectDomain；其值与目录绑定一致。session/review的projectContractVersion从1升级为2；v1继续可读可回放，未知版本拒绝。

```json
{"projectContractVersion":2,"questions":[{"projectEvidence":{"project":{"projectId":"11111111-1111-4111-8111-111111111111","projectDomain":"project/12306"}}}]}
```

这是差异节选，不是完整session。project对象原有displayName、basis、resumeVersion、resumeClaimIds、sourceRevision仍必需。review继承源session的项目合同版本，所有引用和不可变规则保持。混合mock的一场session可以包含多个projectDomain，逐题校验；不能在session顶层用一个projectDomain覆盖整场。

专用事件继续namespace=interview、projectionName=interview；已有domain字段如java-backend/backend-project-learning描述知识或会话类型，**不改作项目路由**。projectDomain与projectId通过project元数据关联；快照仍是既有project_summary、project_attempt、project_weakness派生行。该字段不是把同一次问答再复制到profile域。

用户输入project/12306 → project.list精确取得UUID → 既有interview/interview按projectId查询 → 保留原答、提示与当前评价，换条件提问。新尝试追加，新复盘版本替换旧评价；不重新实现之前的独立通过、回顾排除、归约子页或归档算法。

## 7. 日次、切换与历史连续性

开始一天：只读project.list目录，分别分页读取已绑定project/*的learning-outline，并读取一次旧profile/backend-project-learning作为历史兼容来源。按Asia/Shanghai昨日日期筛实际讲授记录；每个投影单独保持revision，不假称跨项目读到了同一全局时刻。

旧提纲只按已确认projectId的subjectKey归属读取，无法确定就标未知，不按相似项目名认领。新旧视图显示同一条事件时按原eventId/sourceRef去重，保留原出处。只在新域写今后发生的真实事实；**不重发旧事件、不改旧eventKey/domain、不自动搬迁历史**。旧域在这次升级中只是历史只读来源，其他技能未受本次授权不得批量改路由。

目录条目尚无提纲、projection不存在、building=true、工具缺失和分页失败分别报告；都不是用户零分或未掌握的证据。没有可靠昨日框架就说明记录不足；可按用户自述继续当轮回顾，但不把回顾表现回填。

状态顺序仍为DAY_OPEN→RECAP→RECAP_FEEDBACK→TODAY_PLAN→TEACH→FORMAL_QA。RECAP及其反馈0次业务写入，不能写outline旁路保存。真正讲完新单元才能写新域提纲。用户明确要求专项复测时，另起正式问题和attempt；不能事后把回顾题改标签。

缺新feature时停止新项目域读写，继续普通教学或只读明确的旧路径，报告“project/12306尚未同步”。不悄悄把待保存事实写到旧domain，不调用账户注册/切换，不绕过MCP访问Drive/D1/HTTP。

## 8. 其它沿用要求

项目学习与面试继续循循善诱、源码可定位、一次一道题；用户说停止就收束。模拟面试使用已确认简历项目、该项目快照、公开面经线索与官方技术资料，保持校招训练L1—L4递进；网络证据只用于其能够支持的结论，不捏造内部录用线或当季考频。未取得真实简历不得将教学项目冒充个人经历。

pending只证明本机排队；d1_committed只证明D1接纳；projected与archived分别查询原ID核对。唯一submit_event接收结构化JSON；不支持随意base64/二进制/原始录音上传。归档由Worker管理规范JSON，不能因domain带斜杠就创建用户指定远端路径。

## 9. 实施与验收边界

本次必须增量覆盖Creator模板schema/validator、RDS域校验与接纳绑定、目录查询与游标、项目合同v2、学习/模拟面试/复盘调用方及相关合同测试。0008保持原样，新增0009迁移。先取得当前工作树基线，不能把已存在上一版实现再当新代码重写；其通过情况需独立复核，不从文件存在或旧文档推断。

按配套计划先完成合同和迁移前审阅，再实施及回归。交回精确diff、测试日志、完整样例和验收状态。设计QA、合成输入和builder check只证明材料/设计，不表示运行时已通过。用户自行提交；本轮不提交、不部署、不安装、不写个人RDS、不做旧数据搬迁。
