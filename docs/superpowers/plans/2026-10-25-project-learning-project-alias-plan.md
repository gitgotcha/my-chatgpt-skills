# project-12306 项目入口 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 执行方式已指定：DeepSeek 实施，用户提交，Codex 复核；不自动 commit/push/安装/部署。

**Goal:** 通过 project-12306 等可读入口定位稳定项目，打通学习、真实作答、评价、指定项目变式与次日回顾。

**Architecture:** 存储继续使用 profile/backend-project-learning 和 interview 专用事件。项目学习 Skill 通过既有 generic 1.0 的中性 project-binding 观察保存用户确认，从完整同 revision 投影解析别名，正式问答仍按 UUID 关联。无需新增 RDS 分域协议。

**Tech Stack:** 现有 Python 标准库/unittest、JSON Schema、Node.js≥22 ES modules、RDS V2、Markdown/PNG。

**Spec:** [设计 v3](../specs/2026-10-25-project-learning-project-alias-design.md)；[24条验收及完整对话](../specs/2026-10-25-project-learning-project-alias-acceptance.md)。同日 project-domain v2 已撤销，不执行其 Creator1.1/新域/迁移任务。本计划仅补齐当前工作树，不重建2026-10-24已存在的项目面试实现。

## Global Constraints

- S=`C:/Users/27846/my-chatgpt-skills`；R=`C:/Users/27846/my-chatgpt-mcp-v2`；路径S/R均按此展开。现有工作树和未提交改动是实施基线，不按HEAD覆盖。
- projectAlias完整匹配`project-[a-z0-9](?:[a-z0-9-]{0,54}[a-z0-9])?`，总长9—64；明确使用project-12306，不自动接受斜杠写法。
- domain固定backend-project-learning；sourceSkill=software-project-learning；namespace仍profile/interview。正式问答DTO不增加projectAlias/projectDomain。
- storageVersion=2；envelope="1.2"；generic="1.0"；静态capability="1.0"；projectContractVersion=1；buildContractVersion不变。
- generic两个维度：learning-outline和project-binding，均只observed；绑定evidence为≤2048 UTF-8字节的严格五字段JSON，未知字段/重复键拒绝。
- 仅submit_event；capabilities→凭据user.resolve→projection.read；不注册/切换账户，不直接Drive/D1/HTTP、不上传源码/录音/base64、不构造路径。
- generic完整读取每页limit=50、最多20页、累计≤5MiB；同revision、building=false、读到nextCursor=null。仅允许整次重启一次，仍失败则unresolved。
- 没有服务端原子唯一别名保证；冲突fail-closed。绑定eventKey须已projected并在活跃读回中可见，才进行依赖别名的正式操作。
- 回顾binding/outline/attempt/review/附件均0写，不计正式复测；实际首答不覆盖，提示/答案曝光如实标记。
- 无Creator schema/validator、RDS domain语法、新目录操作或数据库迁移。若现有接口不足，交回blocked和最小差异提案，不能自行扩大协议。

## Review Focus

1. 历史observation残留使已撤销绑定复活：PD2测试invalidated_binding_is_not_resolved_from_observation_rows。
2. 前几页看似唯一但末页有冲突：PD2测试partial_projection_never_resolves_unique_alias。
3. outline有UUID但无session目录：PD4测试outline_only_project_reuses_confirmed_uuid。
4. 回顾里确认别名或回答精彩引发旁路保存：PD3/PD5测试recap_never_binds_or_persists_answers。
5. 同题看过答案被当成独立复测：PD4/PD5测试answer_shown_is_not_independent_pass。

## 审阅配置与任务编号

保留PD0—PD6作为修订后的任务编号，任务内容以本文件为准；原v2的协议扩展任务全部撤销。DeepSeek环境的模型精确ID、源代码/日志访问、推理参数与分发接口尚未核实，因此判断型gate均为model=null、status=blocked_model_config、execution_mode=manual_handoff。不得用当前会话模型冒充目标环境配置。执行前登记真实模型清单及验证日期，再将相应gate置pending；此状态不妨碍交付设计。

统一审阅提示：只读命名任务，不修改代码。先读设计、实际基线和原始日志，再看实施者解释。返回pass/changes_required/insufficient_evidence；每个问题给位置、证据、影响、是否阻塞、验证办法。结论只适用命名输入版本；修复重评；同一阻塞两轮未解决则交已核实更强审阅模型或人工裁决。缺证据不是通过。

## PD0：保护工作树与运行基线（light）

依赖：无。Files：只读S/R；Create实施输出目录的baseline-report.md，不写Skill运行目录。

Interfaces：输入=当前两仓库HEAD、dirty清单和交接包source-evidence.json；输出=受影响文件哈希、原diff、环境、原失败和可复现命令。

- [ ] 分别记录`git status --short`、`git rev-parse HEAD`及当前受影响文件diff和哈希，不重置工作树。
- [ ] S运行`python -m unittest discover -s software-project-learning/tests -v`及conducting-java-backend-mock-interviews/tests、reviewing-java-backend-interviews/tests、profile-aware-skill-creator/tests和顶层tests的同类命令。
- [ ] R运行`npm test`；不足环境记blocked/not_run，已有失败单列。
- [ ] 记录Creator最新接口规范与共享runtime的账户注册说明差异，本次只允许凭据核对；不扩散修改其他技能。
- [ ] 交回基线报告，不提交、不读取或写入个人RDS。

Review waiver：仅确定性清单、哈希与原始基线记录，无需模型判断。

## PD1：别名及中性绑定合同（deep）

依赖：PD0。Files：Modify `S/software-project-learning/references/profile-contract.md`、`schemas/profile-capability.json`、`tests/test_profile_contract.py`；Create `references/project-alias-contract.md`、`scripts/project_context.py`、`tests/test_project_context.py`。

Interfaces：新模块纯函数 `validate_project_alias(value: str) -> str` 返回原字符串；`parse_binding_evidence(text: str, subject_key: str) -> dict` 返回设计§4严格五字段对象；非法时抛ProjectContextError并提供code。禁止I/O、ID生成、账户选择。ProjectContextError在本模块定义并导出。

- [ ] RED：test_alias_exact_prefix_and_length、test_alias_rejects_trailing_newline_and_encoding、test_binding_rejects_unknown_and_duplicate_keys、test_binding_subject_matches_alias、test_binding_utf8_byte_limit。断言设计的精确边界及错误，不用只检查正则文本。
- [ ] 运行`python -m unittest discover -s software-project-learning/tests -p test_project_context.py -v`确认因缺功能失败。
- [ ] 实施两纯函数；capability保留1.0/domain/sourceSkill，只添加project-binding维度与真实确认记录条件；recordWhen和sourceRefPolicy按维度明确分支，不能把outline的讲授消息要求套在绑定确认上；两个维度均无成绩语义。
- [ ] GREEN后运行`python profile-aware-skill-creator/scripts/validate_profile_skill.py --mode profile software-project-learning`和原profile测试。Creator schema/validator哈希不变。
- [ ] 输出差异与测试日志，不生成或提交绑定事件。

```yaml
review:
  id: G1
  tasks: [PD1]
  phase: post_implementation
  after: [PD1]
  blocks: [PD2, PD3]
  level: deep
  status: blocked_model_config
  model: null
  execution_mode: manual_handoff
  reason: 别名解析、业务维度与严格现有协议需一致
  inputs: [设计第2至4节, PD1差异及基线哈希, 纯函数与Creator测试原始输出]
  checks: [固定domain和版本, 严格五字段, 元数据不作成绩, 未修改Creator验证器]
  pass_when: [边界测试和原回归通过, 无阻塞问题]
  on_failure: 修复PD1并重跑受影响合同测试
  on_unavailable: 保持阻塞，核实DeepSeek审阅配置或人工接手
```

## PD2：完整投影解析与只读计划（critical）

依赖：G1、G2-pre。Files：Modify PD1的project_context.py及test_project_context.py；Create `S/tests/fixtures/project_alias/projection-pages.json`（隔离合成数据）。R源码只读，不能为简化解析改变远端合同。

Interfaces：`resolve_project_alias(identity: dict, alias: str, pages: list[dict]) -> dict`；固定结果键status/binding/revision/evidenceRefs/reason。status∈resolved/not_found/unresolved/conflict；只有resolved带binding。identity必须已verified且userId与generic summary一致。not_found仅指成功完整读取后无活跃绑定，不等价没有历史项目。`build_project_read_plan(binding: dict) -> dict`返回固定profile域查询及interview UUID查询，不执行I/O。

- [ ] RED：完整页唯一绑定返回resolved；相同五字段重复观察允许；不同UUID、同UUID多别名、basis变化为conflict。invalidated_binding_is_not_resolved_from_observation_rows只使用summary活跃evidenceRefs关联event_activity。
- [ ] RED：partial_projection_never_resolves_unique_alias；最后页冲突、缺event_activity引用、不同revision/用户、building=true、20页/5MiB边界均覆盖；不传generic尚未支持的过滤参数。
- [ ] 运行PD1同命令记录RED。按设计§5实施，结果不包含无关用户/项目答案；错误不回退到最后写入获胜。
- [ ] GREEN；使用当前R的generic reducer和query隔离夹具确认读取形状真实可用，尤其supersede/invalidate后的summary活跃引用。若不符交回blocked，不自行改RDS。
- [ ] 输出只读计划夹具与投影结果日志，证明没有Outbox/业务写入。

```yaml
review:
  id: G2-pre
  tasks: [PD2]
  phase: pre_implementation
  after: [G1]
  blocks: [PD2]
  level: critical
  status: blocked_model_config
  model: null
  execution_mode: manual_handoff
  reason: 错误映射会将实际回答归入错误项目
  inputs: [设计第5节, R当前query及generic投影源码, PD2负向测试设计]
  checks: [凭据范围, 完整revision, 活跃证据解析, 半页和冲突关闭路由]
  pass_when: [读取形状由源码支持, 负向边界齐全, 无阻塞问题]
  on_failure: 修订解析和测试设计后才实施PD2
  on_unavailable: 阻塞PD2，交由已核实模型或人工审阅
```

```yaml
review:
  id: G2-post
  tasks: [PD2]
  phase: post_implementation
  after: [PD2]
  blocks: [PD4]
  level: critical
  status: blocked_model_config
  model: null
  execution_mode: manual_handoff
  reason: 需实际负向证据证明不会串项目或复活失效绑定
  inputs: [PD2精确差异, 同revision投影夹具和原始测试输出, G2-pre记录]
  checks: [完整读取才resolved, 无跨用户缓存, 修订生效, 不调用新RDS接口]
  pass_when: [设计所有解析状态有实测结果, 无阻塞问题]
  on_failure: 修复PD2并重跑相关解析用例
  on_unavailable: 阻塞PD4，不以文字解释代替测试
```

## PD3：绑定构造、回执和回顾门禁（critical）

依赖：G1、G3-pre；可与PD2独立测试，不共享产品改动区域。Files：Modify project_context.py/test_project_context.py及profile合同；不改原plan_turn_writes返回结构。

Interfaces：`build_project_binding_payload(identity: dict, binding: dict, *, event_id: str, event_key: str, observed_at: str, source_ref: str) -> dict`返回既有`{domain,event}` payload，校验identity已verified但不将身份重复塞入内部event；调用方按原1.2 envelope封装。`plan_project_binding_write(context: dict, resolution: dict, confirmation: dict) -> dict`返回allowed/reason；只在显式配置阶段有实际可定位确认、无冲突且当前完整读取有效时allowed，或满足设计§5的首次新建引导例外；recap恒false。不发请求/造ID。读回确认由Skill按原eventKey执行，不由纯函数假称已保存。

- [ ] RED：无真实确认/sourceRef、recap即使带确认、身份不符、conflict均不构造；unresolved默认拒绝，只有projection_not_found且已明确独立新建、无已知pending、caps/身份成功时允许首次引导。building/超时/不完整页或“沿用之前项目”不得走例外。
- [ ] RED：同一重试payload和ID不变；pending/d1_committed不能当resolved；projected但活跃evidenceRefs不含本eventKey仍未确认；并发冲突关闭路由。
- [ ] 运行context测试记录RED，再实施最小构造与门禁；绑定不伪装成教学，不增加outline/attempt。
- [ ] GREEN并运行project_evidence和profile原测试；用隔离Outbox/投影夹具检查重试与失效修订，不写个人账户。
- [ ] 交回回执状态轨迹，明示无服务端原子唯一性保证。

```yaml
review:
  id: G3-pre
  tasks: [PD3]
  phase: pre_implementation
  after: [G1]
  blocks: [PD3]
  level: critical
  status: blocked_model_config
  model: null
  execution_mode: manual_handoff
  reason: 绑定事实与回顾零写入必须有明确授权和阶段边界
  inputs: [设计第4至5及8节, 现有project_evidence门禁, PD3测试设计]
  checks: [真实确认, 原ID重试, 回顾优先, 读回前不启动依赖路由]
  pass_when: [构造和回执职责明确, 无阻塞问题]
  on_failure: 修订门禁和回执设计后再实施
  on_unavailable: 阻塞PD3，核实配置或人工接手
```

```yaml
review:
  id: G3-post
  tasks: [PD3]
  phase: post_implementation
  after: [PD3]
  blocks: [PD4]
  level: critical
  status: blocked_model_config
  model: null
  execution_mode: manual_handoff
  reason: 需证据证明没有旁路保存或虚报完成
  inputs: [PD3差异, 构造/门禁/重试日志, G3-pre记录]
  checks: [回顾所有业务写0, 无重复身份字段, 回执阶段准确, 冲突保留原事实]
  pass_when: [负向和原回归通过, 无阻塞问题]
  on_failure: 修复PD3并重跑门禁测试
  on_unavailable: 阻塞PD4，保留未审阅状态
```

## PD4：学习、模拟面试与复盘接线（deep）

依赖：G2-post、G3-post。Files：Modify `S/software-project-learning/SKILL.md`、`references/project-evidence-contract.md`、`references/standard-mode.md`、`references/interview-mode.md`、`references/detailed-lesson-format.md`、`tests/behavior-scenarios.md`和test_project_context.py；最小修改 `S/conducting-java-backend-mock-interviews/references/project-targeted-interview.md`、`references/candidate-profile-integration.md`、`scripts/project_question_plan.py`及对应tests/test_project_question_plan.py；复盘仅在入口需要时加合同链接，不修改评分算法。

Interfaces：调用PD2解析结果与读计划；现有build_learning_session、prepare_review_handoff、question plan仍接收既有projectId/basis，签名和版本不变。不得把别名加进严格session/question schema。

- [ ] RED：outline_only_project_reuses_confirmed_uuid；project-12306切project-pig-rpc不会继承前者题目/缓存；未答无session；assisted不算独立通过；每次原答只提交一次。
- [ ] 运行context、project_evidence、mock question plan及跨Skill合同测试，确认缺失行为。
- [ ] 更新流程：学习先讲后问；mock先问后评；只读别名后用UUID获取快照；评价始终由复盘owner提交；次日回顾读取昨日提纲并零写入。
- [ ] 保留简历个人贡献、源码事实、设计场景、合成输出、真实实验的边界。联网候选优先官方资料并记日期/版本；不把社区频次说成字节必考。
- [ ] GREEN后运行三技能原回归与顶层合同测试，校验原schema/manifest不因本次变化而无故升级。
- [ ] 交回接口调用轨迹和两项目隔离证据。

```yaml
review:
  id: G4
  tasks: [PD4]
  phase: post_implementation
  after: [PD4]
  blocks: [PD5]
  level: deep
  status: blocked_model_config
  model: null
  execution_mode: manual_handoff
  reason: 跨Skill证据owner及不同教学模式容易混淆
  inputs: [设计第6至8节, PD4差异, 两项目和跨Skill测试原始输出]
  checks: [UUID连续, session不加别名字段, 学习与mock曝光分开, 回顾不补录]
  pass_when: [旧合同回归和新接线通过, 无阻塞问题]
  on_failure: 修复PD4并重跑受影响Skill测试
  on_unavailable: 阻塞PD5，交回未审阅部分
```

## PD5：完整输出与模型行为验收（deep）

依赖：G4。Files：Modify `S/software-project-learning/tests/behavior-scenarios.md`；必要时更新同技能references/examples/ticket-query-rds-complete-dialogue.md中合同说明，保留完整教学内容与三PNG；Create实施输出目录behavior-traces/。

Interfaces：输入=验收矩阵A01—A24和交接包完整教学样本；输出=逐case result、实际模型对话、工具调用日志、来源索引。合成单测不能替代模型行为运行。

- [ ] 执行A13—A21真实模型行为回放：余票完整课、未答停止、看过答案、mock、次日回顾、RPC切换、指定项目变式。个人身份和RDS由隔离适配器替代。
- [ ] 验证可见图片/时序图、真实核验源码定位、详细注释和仅一道底部题；无源码环境记blocked_source，不伪造行号。原教学样本不是本轮实验。
- [ ] 对回顾轨迹计数：业务事件/Outbox/session/review/outline/binding/附件写入全部0。
- [ ] 对每个case列pass/fail/blocked/not_run及证据路径；修复失败范围后只重跑相关用例。

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
  reason: 静态文案正确不保证大模型真实行为
  inputs: [验收A13至A21, 完整对话与工具轨迹, 源码/官方资料证据]
  checks: [输出完整且图可见, 提问时机正确, 无伪造事实, 回顾0写入]
  pass_when: [A13至A21所需行为验收有实际证据且通过, 无阻塞问题]
  on_failure: 修复对应教学约束并重跑相关场景
  on_unavailable: 阻塞PD6的完成声明，保留现有材料
```

## PD6：联合核验与交回（light，机械打包）

依赖：G5；判断性验收由前述gate完成。Files：Create实施输出目录delivery-report.md、case-results.json、SHA256SUMS.txt及差异包；产品源码不新增运行报告。

Interfaces：输入=PD0基线、当前diff、真实日志、全部gate记录；输出=用户可审阅交接，不自动提交。

- [ ] 重跑受影响Skill、Creator profile校验、顶层合同；若R没改源码，使用PD2/PD3隔离验证日志和PD0原基线，不无故重复全套云测试。
- [ ] 核对A01—A24逐项结果，缺环境保留blocked/not_run，不能用文档QA填pass。
- [ ] 核对产品改动仅限本方案范围，旧v2新域/版本/迁移任务均未执行；保护既有dirty改动。
- [ ] 交回实际修改文件、差异、命令/退出码、行为轨迹、在线能力核验状态和未完成项。若需云端部署，作为用户后续单独提交动作。
- [ ] 用户提交后由Codex读取实际文件与原始输出并重跑检查，才接受实现；本轮不安装、不push、不宣称上线。

Review waiver：本任务只有清单、哈希、状态和打包的机械核对；不得用该豁免绕过前述判断型gate。

## 依赖与交接

PD0→PD1→G1；G1→G2-pre→PD2→G2-post；G1→G3-pre→PD3→G3-post；G2-post和G3-post→PD4→G4→PD5→G5→PD6。无环。PD2/PD3逻辑独立但共享文件，同一实施者顺序修改，避免并行覆盖。

当前只完成设计材料。产品任务、未来审阅gate和A01—A24均未运行。独立builder check因工具额度不足未能执行，已由作者按源码与合同自查；不称独立审阅通过。
