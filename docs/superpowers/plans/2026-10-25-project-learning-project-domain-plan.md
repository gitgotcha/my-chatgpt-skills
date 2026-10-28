> **已被 v3 取代，历史参考，不执行本文件任务。** 用户选择固定 domain＋稳定项目 ID，入口名为 `project-12306`，前缀 `project-`。以下旧斜杠分域、Creator1.1、projectContractVersion2及迁移方案撤销。请改读 [2026-10-25-project-learning-project-alias-plan.md](2026-10-25-project-learning-project-alias-plan.md)。

# 项目学习 project/12306 分域 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 延续用户指定的DeepSeek实施、用户提交、Codex复核；不自动commit/push/安装/部署。

**Goal:** 让同一项目学习Skill按project/<slug>保存上下文，并与原项目UUID和面试快照保持一致。

**Architecture:** 增量支持受限项目domain，扩展Creator静态模板合同与RDS目录绑定。课程提纲走profile/project/<slug>；正式作答仍走interview专用事件，经相同UUID关联。不迁移或重发旧事实。

**Tech Stack:** 现有Node.js≥22 ES modules、Python标准库/unittest、JSON Schema子集校验器、Worker/D1/SQLite Outbox和Markdown/PNG。

**Spec:** [2026-10-25-project-learning-project-domain-design.md](../specs/2026-10-25-project-learning-project-domain-design.md)。同时读取[验收与分域示例](../specs/2026-10-25-project-learning-project-domain-acceptance.md)。本计划是上一版实现上的新增工作，不取代2026-10-24计划的既有任务与记录。

## Global Constraints

- S=`C:\Users\27846\my-chatgpt-skills`；R=`C:\Users\27846\my-chatgpt-mcp-v2`。下文S/R路径均按此展开。所有Modify路径已核实，Create是待新增。
- 新domain严格匹配`^project/[a-z0-9](?:[a-z0-9-]{0,54}[a-z0-9])?$`；总长≤64，slug1—56；原flat规则不变。
- namespace不变；sourceSkill/dimensionKey不放宽；静态模板不作为wire domain；不产生远端目录路径。
- 存储版本2、业务envelope1.2、generic event1.0、静态capability1.1、projectContractVersion2各自独立；已有buildContractVersion2不升级。
- 新域只能使用凭据身份与submit_event；不注册/切换账户、不直接Drive/D1/HTTP、不上传任意文件/base64。
- 回顾完全零写入；教学提纲仅observed；原题原答不覆盖；评价归复盘Skill；不重复累计到generic画像。
- 旧projectContractVersion1和flat domain继续可读可回放；旧backend-project-learning只是历史读取来源，不重发旧事件。
- 保留工作树已有实现和用户改动；0008不改写，新增0009迁移；不在S的冻结旧Worker/MCP中实现新V2。
- 每任务交回命名差异与验证证据，替代自动提交步骤。真实云测不得使用本包合成数据写个人账户。

## Review Focus

1. 教学先于答题时UUID丢失 → PD3测试outline_first_binds_same_uuid_used_by_later_session。
2. 旧v1分支的`===1`使v2悄悄不进入归约 → PD2/PD6测试v1_v2_session_review_projected_and_replayed。
3. 有slash的domain被当作目录、或放宽dimensionKey → PD1/PD2测试project_domain_is_not_a_path_and_other_identifiers_remain_flat。
4. 切到新项目后昨日框架无入口 → PD4/PD5测试recap_discovers_yesterday_across_domains_with_zero_writes。
5. 目录翻页时补绑旧项目导致跨页漏项 → PD3/PD4测试domain_binding_bumps_directory_revision_and_invalidates_old_cursor。

## 审阅配置

DeepSeek目标环境的精确模型ID、访问源码/日志能力和调用入口尚未核实。以下判断型gate设`blocked_model_config`、model=null、manual_handoff；不替用户猜模型或计费参数。这是执行前的配置前置条件，不阻碍本设计交付。

执行人先登记真实可用模型及证据，随后将gate设pending。每个gate统一使用本提示词，并带入其inputs/checks：

> 只读审阅该gate任务，不修改代码。先检查原始设计、基线、测试设计或实际diff/日志，再看实施者解释。返回pass、changes_required或insufficient_evidence；每个问题给位置、证据、影响、是否阻塞与验证方式。不把缺失测试当通过。结论只适用命名输入版本；修复后重评。连续两轮同一阻塞未解决，转已验证更强审阅模型或人工裁决，不以投票判定。

## PD0：保留当前工作树并建立基线（light）

依赖：无。Files：只读S/R当前源代码；Create交回物baseline-report.md（放实施输出目录，不混进技能运行资源）。

Interfaces：输入=当前HEAD、dirty清单与本包source-evidence.json；输出=两仓库基线、变更前文件哈希、测试环境、原失败与可复现命令。

- [ ] 分别运行`git status --short`与`git rev-parse HEAD`；保存受影响文件的当前完整diff和哈希。不能按旧HEAD覆盖已有未提交实现。
- [ ] S运行`python -m unittest discover -s profile-aware-skill-creator/tests -v`、`python -m unittest discover -s software-project-learning/tests -v`、`python -m unittest discover -s conducting-java-backend-mock-interviews/tests -v`、`python -m unittest discover -s reviewing-java-backend-interviews/tests -v`、`python -m unittest discover -s tests -v`。
- [ ] R运行`npm test`，保存退出码；环境或依赖不足记blocked/not_run。已有失败单独列，不当本次修复成果。
- [ ] 只运行纯校验确认旧flat通过、project/12306当前拒绝；不发送该domain写入云端。
- [ ] 输出基线报告；不提交。

Review waiver：本任务只做可重复的清单、哈希与测试基线记录，确定性核验代替模型判断。

## PD1：Creator静态模板合同1.1（deep）

依赖：PD0。Files：

- Create `S/profile-aware-skill-creator/schemas/profile-capability-v1.1.schema.json`。
- Modify同技能`scripts/validate_profile_skill.py`、`references/profile-authoring-standard.md`、`references/rds-v2-interface-and-file-format.md`、`SKILL.md`、`README.md`。
- Modify同技能`tests/test_validate_profile_skill.py`、`tests/test_meta_skill_contract.py`；Create `tests/test_project_domain_template.py`。

Interfaces：`_load_capability_schema(version: str = "1.0") -> object`按版本选择两份schema，缓存按版本分开；`validate_project_template(document:dict)->list[str]`校验1.1固定模板与参数元数据。旧1.0 schema文件保持字节不变；`SAFE_ID`仍检查sourceSkill/dimensionKey。

- [ ] RED：1.1固定模板通过；混写domain/domainTemplate、未知版本/前缀/占位符拒绝；1.0原技能仍通过；不能把模板当wire domain；sourceSkill含slash仍拒绝。
- [ ] 执行`python -m unittest discover -s profile-aware-skill-creator/tests -v`确认失败来自缺功能。
- [ ] 实施版本选择与手写字段检查同步，不能只改JSON Schema。runtime1.1增projectDirectoryReadEvent=project.list，未知字段拒绝；注册/切换仍禁止。
- [ ] 同命令GREEN，运行已有所有Creator用例，保存1.0 schema未变的哈希证据。
- [ ] 输出diff与新增合同夹具，不生成运行学习事件。

```yaml
review:
  id: G1
  tasks: [PD1]
  phase: post_implementation
  after: [PD1]
  blocks: [PD2, PD5]
  level: deep
  status: blocked_model_config
  model: null
  execution_mode: manual_handoff
  reason: 静态schema、自制解释器与手写检查需保持一致
  inputs: [本设计第3至6节, PD1差异, 1.0哈希, Creator测试输出]
  checks: [旧合同不变, 模板有限且无任意表达式, 其它标识不放宽, 不把静态声明当在线能力]
  pass_when: [正负夹具均有结果, 无阻塞问题]
  on_failure: 修复PD1并重跑版本兼容测试
  on_unavailable: 保持阻塞，核实DeepSeek审阅模型或人工接手
```

## PD2：域校验与项目合同v2跨端一致（deep）

依赖：G1。Files：

- Modify `R/services/reliable-drive-sync-worker/src/generic-profile-contract.js`、`src/protocol.js`、`src/rds2/project-contract.js`。
- Modify `R/services/reliable-drive-sync-worker/src/rds2/project-repository.js`及`src/rds2/projection/project-interview.js`中版本识别分支；按实际调用同步`src/rds2/projection/interview.js`、`src/profile-model.js`，避免漏掉旧的===1判断。
- Modify `S/reviewing-java-backend-interviews/scripts/interview_core.py`、`S/conducting-java-backend-mock-interviews/scripts/mock_handoff.py`、两技能各自`schemas/contracts.schema.json`及manifest.json。
- Create `R/services/reliable-drive-sync-worker/test/rds2-project-domain-contract.test.js`、`S/tests/test_project_domain_contract_parity.py`；扩展既有project contract测试。

Interfaces：JS导出`parseProjectDomain(value:string)->{projectSlug:string}|null`、`validateProjectRef(ref:object,domain:string):void`；前者对有效flat域返回null，对合法project域返回解析结果，对非法输入抛invalid_domain。Python实现对应`parse_project_domain`。`validateGenericProfileDomain`仍返回合法原字符串，不做静默标准化。

ProjectRef是设计6.3的严格四字段对象；专用Project元数据在v2增加projectDomain，其余字段不变。通用profile payload新增projectRef只适用于project/*；内部generic event字段不增加。新项目域教学内容限制由新增`validateProjectOutlineEvent(event,projectRef):void`验证：仅learning-outline、subjectKey UUID匹配、observed、sourceRef结构有效；对文字真伪不作程序能够证明的承诺。

- [ ] RED：共享域矩阵覆盖合法slug、1/56/57字符、大小写、点段、编码斜杠/百分号、Unicode；JS/Python/Creator同结果。明确区分合法flat的project与新项目格式。
- [ ] RED：projectContractVersion1/2都通过正确形状；v1夹入projectDomain拒绝；v2缺domain拒绝；review继承源版本；混合mock逐题路由不被会话顶层覆盖；v2仍走原容量限制和profileChanges隔离。
- [ ] R运行`node --test services/reliable-drive-sync-worker/test/rds2-project-domain-contract.test.js`；S运行`python -m unittest discover -s tests -p test_project_domain_contract_parity.py -v`，保留RED证据。
- [ ] 实施严格分支与错误码，扫描受影响源码所有projectContractVersion判断并逐处说明；不粗暴将1替换成2。已有buildContractVersion2和rowKind保持。
- [ ] 同命令GREEN，回归旧generic-profile-contract、project-contract和Python helper测试。两份schema保持逐字节一致。
- [ ] 输出diff、版本分支清单及测试结果。

```yaml
review:
  id: G2
  tasks: [PD2]
  phase: post_implementation
  after: [PD2]
  blocks: [PD3]
  level: deep
  status: blocked_model_config
  model: null
  execution_mode: manual_handoff
  reason: 三端校验和旧版本分支可能让新事件静默丢失
  inputs: [设计第5至6节, PD2差异, 共享正负矩阵, 版本分支清单与测试输出]
  checks: [仅有限域放宽, v1不重写, v2不被忽略, generic内部无身份重复, 两份schema一致]
  pass_when: [合同等价且旧回归通过, 无阻塞问题]
  on_failure: 修复PD2并补漏掉的消费者测试
  on_unavailable: 阻塞PD3，先取得有效审阅配置
```

## PD3：增量迁移与原子目录绑定（critical）

依赖：G2、G3-pre。Files：

- Create `R/services/reliable-drive-sync-worker/migrations/0009_rds2_project_domains.sql`。
- Modify `R/services/reliable-drive-sync-worker/src/rds2/project-repository.js`、`src/rds2/events/accept.js`。
- Create `R/services/reliable-drive-sync-worker/test/rds2-project-domain-accept.test.js`。
- Modify `R/tools/reliable-drive-sync-mcp/local-outbox-v2.mjs`中新增永久冲突码分类、对应`test/local-outbox-v2.test.mjs`（其余重试策略不改）。

Interfaces：`planProjectDomainBinding({principal,projectRef,existing})->{inserts,updates,errors}`纯函数；`prepareProjectDomainBinding({io,principal,envelope})->object`有界读取；生成的SQL与原accept batch一起提交。共用`bumpProjectDirectoryRevisionStatement(db,userId)`，所有实际目录项变更（包括旧v1新项目）都经过它。幂等replay/alias不重复加revision。

- [ ] pre gate通过后RED：outline_first_binds_same_uuid_used_by_later_session；旧NULL记录补绑不换UUID；同domain不同UUID、同UUID不同domain、basis不匹配拒绝；不同用户相同domain允许。
- [ ] RED：并发首次绑定只有一致结果；事件接纳失败不留下映射/revision半变更；同请求重试只增一次目录版本；旧v1新增项目也使目录版本变化；开关false无新域写入。
- [ ] `node --test services/reliable-drive-sync-worker/test/rds2-project-domain-accept.test.js`记录RED。
- [ ] 0009仅增加可空列、唯一索引、目录revision表；本地已有旧行保持NULL；不修改0008，不扫描displayName回填。feature开关RDS2_PROJECT_DOMAIN_ENABLED默认false。
- [ ] 在原事务中实现绑定/计数；冲突成为明确业务错误而非无限重试或泄漏SQL。新永久错误在Outbox blocked保留原包，不能复用其它用户receipt。
- [ ] GREEN后运行现有project-accept/schema-identity/Outbox测试；输出迁移前后隔离库内容和竞争测试证据，不执行生产迁移。

```yaml
review:
  id: G3-pre
  tasks: [PD3]
  phase: pre_implementation
  after: [G2]
  blocks: [PD3]
  level: critical
  status: blocked_model_config
  model: null
  execution_mode: manual_handoff
  reason: 跨namespace共用身份映射与增量唯一约束
  inputs: [设计第5节及目录合同, 当前0008和accept源码, PD3测试设计]
  checks: [没有并行身份真源, 教学先于答题可绑定, 原子唯一约束, 旧数据不自动归属, 开关服务端生效]
  pass_when: [迁移与竞争用例明确, 无阻塞问题]
  on_failure: 修订方案/测试后才实施PD3
  on_unavailable: 阻塞PD3，转已核实模型或人工审阅
```

```yaml
review:
  id: G3-post
  tasks: [PD3]
  phase: post_implementation
  after: [PD3]
  blocks: [PD4, PD6]
  level: critical
  status: blocked_model_config
  model: null
  execution_mode: manual_handoff
  reason: 真实事务与幂等必须验证
  inputs: [PD3精确差异, 本地迁移/竞争/故障测试原始日志, G3-pre记录]
  checks: [无半绑定, replay不重复计数, NULL历史保留, 跨用户隔离, 冲突不换ID掩盖]
  pass_when: [关键事务负向用例通过, 无阻塞问题]
  on_failure: 修复PD3并重跑相关事务用例
  on_unavailable: 阻塞PD4/PD6，不以文字解释代替证据
```

## PD4：只读目录、feature与精确域查询（critical）

依赖：G3-post、G4-pre。Files：

- Modify `R/shared/rds2-protocol.mjs`、`R/services/reliable-drive-sync-worker/src/rds2/query.js`、`src/rds2/routes.js`。
- Modify `R/tools/reliable-drive-sync-mcp/stdio-bridge.mjs`、`v2-routing.mjs`（如原通道已透传，只补必需的操作白名单，不重写桥接）。
- Create `R/services/reliable-drive-sync-worker/test/rds2-project-directory.test.js`；Modify原`rds2-project-query.test.js`、`rds2-routes.test.js`；扩展bridge现有`test/v2-routing.test.mjs`。

Interfaces：新增`project.list`原生DTO，params仅limit/cursor/projectDomain；返回设计6.2的revision/projects/nextCursor。`projectList(params)`由query executor导出并在routes分发；`projection.read`本身不增加domain参数，直接使用projectionName=project/12306。

- [ ] pre gate通过后RED：按principal查目录；旧未绑定项目可见；domain精确过滤；目录返回不含答案/任意额外字段；profile新domain不能改变namespace或借用他人UUID。
- [ ] RED：cursor换用户/domain/operation拒绝；补绑/新建导致directory_changed；过期重读；50行和256KiB边界；读接口无Outbox/D1写入；project/12306与project/pig-rpc的投影游标不能混用。
- [ ] 运行`node --test services/reliable-drive-sync-worker/test/rds2-project-directory.test.js`取得RED。
- [ ] 实施feature=projectDomainRouting的条件声明；缺迁移的测试环境不能宣称支持。配置关闭则新操作/新域拒绝，旧flat读写继续。
- [ ] GREEN并回归原query/routes/bridge；记录本地feature结果与在线capabilities差异，不自动部署以追平差异。
- [ ] 输出diff、参数/错误矩阵、真实查询与只读断言。

```yaml
review:
  id: G4-pre
  tasks: [PD4]
  phase: pre_implementation
  after: [G3-post]
  blocks: [PD4]
  level: critical
  status: blocked_model_config
  model: null
  execution_mode: manual_handoff
  reason: 新查询及游标影响凭据用户隔离
  inputs: [设计6.2至6.4, 当前query/routes/shared协议, PD4测试矩阵]
  checks: [目录始终按principal过滤, cursor绑定完整, 新旧scope不混淆, 没有任意文件入口]
  pass_when: [负向隔离场景齐备, 无阻塞问题]
  on_failure: 先修订查询/权限测试再实施
  on_unavailable: 阻塞PD4，核实审阅模型或人工接手
```

```yaml
review:
  id: G4-post
  tasks: [PD4]
  phase: post_implementation
  after: [PD4]
  blocks: [PD6]
  level: critical
  status: blocked_model_config
  model: null
  execution_mode: manual_handoff
  reason: 需实证租户、游标、只读和feature门禁
  inputs: [PD4差异, 目录/分页/路由/桥接测试日志, 当前feature结果]
  checks: [越权无泄漏, 目录变化重读, 查询无副作用, 未部署不称在线可用]
  pass_when: [全部安全边界用例通过, 无阻塞问题]
  on_failure: 修复PD4并重跑相关查询回归
  on_unavailable: 阻塞PD6，交回明确未审阅状态
```

## PD5：项目学习与面试调用方增量更新（deep）

依赖：G1、G2；使用隔离夹具可先做，不得在PD4可用前写云端。Files：

- Modify `S/software-project-learning/SKILL.md`、README.md、`references/profile-contract.md`、`references/project-evidence-contract.md`、`schemas/profile-capability.json`、`scripts/project_evidence.py`、`tests/test_profile_contract.py`、`tests/test_project_evidence.py`、`tests/behavior-scenarios.md`。
- Modify `S/conducting-java-backend-mock-interviews/references/project-targeted-interview.md`、`references/candidate-profile-integration.md`、`scripts/project_question_plan.py`及对应测试；仅在实际入口有旧路由时更新其SKILL.md。
- Modify `S/reviewing-java-backend-interviews/references/profile-contract.md`、`references/review-protocol.md`中版本说明；已有helper由PD2修改。
- Modify `S/AGENTS.md`中旧domain连续性段，区分“新事实按project/<slug>”与“旧域只读兼容”；不批量改其它技能的共享runtime文件。新版接口参考通过最小链接复用，不能只改某一份共享副本破坏字节同步。

Interfaces：`resolve_project_domain(project_slug:str)->str`为纯函数；扩展`build_outline_event(...,project_ref:dict|None=None)`：已提供project_ref才生成新域payload，不默认为12306；旧调用保留为显式legacy兼容且主入口不再用于新事实。`build_learning_session(..., project_contract_version:int=1)`与mock helper按版本构造；新feature场景使用2；复盘沿用源版本。

`build_project_read_plan(selected_project, directory, legacy_enabled=True)->dict`为纯读取计划：分别给新域outline查询、历史域兼容读取、interview UUID查询。不给它网络I/O或快照写权限。下一日目录→各domain提纲的跨会话读取由Skill编排，不把数值相同的revision当全局revision。

- [ ] RED：12306/pig-rpc切换读写各自domain；缺绑定不猜UUID；outline先于答题；旧提纲仅按已确认UUID显示；缺feature不偷偷写旧域；主入口无硬编码单一项目。
- [ ] RED：旧提纲有UUID但目录为空，先展示原sourceRef候选、确认后复用原UUID；未确认或旧投影未知时不新造UUID、不保存；旧提纲不重发。
- [ ] RED：recap_discovers_yesterday_across_domains_with_zero_writes；回顾不经过任何写构造器；提示/看答案不计独立通过；普通学习未答题时只有实际教学提纲，不造session。
- [ ] 运行`python -m unittest discover -s software-project-learning/tests -v`取得RED；实施上述纯函数、主入口与画像三件工件。
- [ ] GREEN并运行`python profile-aware-skill-creator/scripts/validate_profile_skill.py --mode profile software-project-learning`、模拟面试和复盘测试。
- [ ] 用配套验收中的完整对话做行为演练，保留真实模型轨迹；当前余票图解/源码完整样本继续作为教学基准，不能退化成分域说明或两个API调用。
- [ ] 输出diff和演练证据，不把合成样例写个人RDS。

```yaml
review:
  id: G5
  tasks: [PD5]
  phase: post_implementation
  after: [PD5]
  blocks: [PD6]
  level: deep
  status: blocked_model_config
  model: null
  execution_mode: manual_handoff
  reason: 跨项目上下文、历史兼容和教学行为需共同验收
  inputs: [PD5差异, profile validator输出, 完整行为轨迹, 原余票教学样本]
  checks: [没有硬编码项目, 回顾零旁路写入, 旧证据不重发, 新domain实际生效, 仍保持时序图/详细源码/底部单题]
  pass_when: [对应行为用例均有证据, 无阻塞问题]
  on_failure: 修复PD5并重演受影响对话
  on_unavailable: 阻塞PD6，不以文档关键词代替行为结果
```

## PD6：联合验证与交回用户（deep）

依赖：G3-post、G4-post、G5。Files：Create `R/services/reliable-drive-sync-worker/test/rds2-project-domains-e2e.test.js`；扩展既有`test/rds2-archive.test.js`；Create `S/tests/test_project_domains_flow.py`。实施报告/日志放输出目录，不混进运行资源。

Interfaces：输入=当前两仓库准确diff和版本；输出=实现报告、逐case结果、完整对话、原始日志、文件哈希和用户待提交清单。结果用pass/fail/blocked/not_run，不能将设计QA挪成产品通过。

- [ ] RED：从旧v1 UUID+旧提纲开始，读目录补绑project/12306，新讲授写新域，正式v2作答进入同UUID快照；切到RPC后回顾昨日12306，0写；随后新讲授写project/pig-rpc；专项复测只取12306。
- [ ] 本地隔离D1/Outbox运行RED；修复只限集成缺口，不能放松合同。
- [ ] GREEN后R运行`npm test`；S重跑PD0各组与新增flow，运行profile模式validator。
- [ ] 离线归档回放v1+v2源事件：项目作答/评价和domain绑定可追溯，domain未变成目录路径；原48KiB/24KiB/8KiB事件边界和build子页预算不变。
- [ ] 逐项填写配套28条验收矩阵；确定性程序测试、模型演练、文档检查、在线烟测分别报告。在线未测则not_run。
- [ ] 交回完整文件diff、证据和未完成项；不提交、部署、安装或自动搬迁旧数据。

```yaml
review:
  id: G6
  tasks: [PD6]
  phase: post_implementation
  after: [PD6]
  blocks: [user_delivery]
  level: deep
  status: blocked_model_config
  model: null
  execution_mode: manual_handoff
  reason: 确认新增分域与上一版实现协同而非另起一套
  inputs: [两仓库命名diff, 28条实际case结果, 测试原始日志, 模型轨迹, 已知限制]
  checks: [新旧历史连续, 单次事实不重计, 身份与目录隔离, 次日跨域回顾零写入, 未部署不称上线, 用户改动保留]
  pass_when: [P0全通过且P1无未说明缺口, 无阻塞问题, 交回物完整]
  on_failure: 返回责任任务修复并回归对应case
  on_unavailable: 保留未审阅状态，不宣称整体通过
```

## 依赖检查

PD0→PD1→G1→PD2→G2→G3-pre→PD3→G3-post→G4-pre→PD4→G4-post；PD5在G1/G2后可按夹具完成→G5；G3-post/G4-post/G5全部通过→PD6→G6。critical的pre在代码前，post在集成前；无循环依赖。

作者本轮仅生成方案和计划；所有产品实施任务与28个产品验收case尚未运行。前版已有实现是否通过，不能从本计划的存在推断。
