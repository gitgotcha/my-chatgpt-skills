# 项目学习设计 v3：project-12306 项目入口与共享证据

日期：2026-10-25，Asia/Shanghai。用户已选择“固定 domain＋稳定 projectId＋项目入口”，并指定入口名称为 `project-12306`，统一前缀为 `project-`。

本文件取代同日 project-domain v2 的斜杠分域方案。交付范围为设计、DeepSeek 执行计划与参考输出；没有实施、安装、数据库迁移、部署或提交个人学习事件。DeepSeek 实施，用户提交，Codex 复核。

配套：[执行计划](../plans/2026-10-25-project-learning-project-alias-plan.md)、[验收与完整对话](2026-10-25-project-learning-project-alias-acceptance.md)。

## 1. 目标与取舍

用同一个 software-project-learning Skill 学习不同项目；用户能说“今天学习 project-12306 的余票展示”“只从这个项目的快照考我”。教学、真实回答、评价各有唯一责任方，历史连续、来源可查。

| 选择 | 收益 | 代价与结论 |
|---|---|---|
| 固定 domain＋projectId＋项目别名 | 复用现有协议，项目改名不打断历史 | 需要 Skill 层别名记录和可靠解析；用户选择此方案 |
| 实际存储 domain=project/<slug> | 适合未来按项目设置独立存储策略 | 需 Creator/RDS 扩展和版本兼容；本次撤销 |
| 实际存储 domain=project-12306 | 符合现有 flat 语法 | 仍将每个项目变成独立存储域；不是本次选择 |

本设计中的别名是可读选择键，不是权限边界、namespace、Drive 路径或 Skill 文件夹名。鉴权始终由服务器凭据绑定用户；跨项目隔离依赖 projectId。

## 2. 命名与版本

| 字段 | 本次固定值/规则 |
|---|---|
| projectAlias | `project-12306`；其他例子 `project-pig-rpc`、`project-ragent` |
| 别名语法 | 完整匹配 `project-[a-z0-9](?:[a-z0-9-]{0,54}[a-z0-9])?`；后缀1—56，总长9—64字符 |
| namespace / domain | 教学与别名：`profile` / `backend-project-learning` |
| 正式作答及评价 | `interview`，使用原有专用项目合同 |
| 项目身份 | 稳定 UUID `projectId`；不从别名、路径、显示名或 commit 推导 UUID |
| sourceSkill | `software-project-learning`，模拟面试仍用自己的 Skill 名称 |
| 版本 | storageVersion=2；envelope schemaVersion="1.2"；generic event="1.0"；静态 capability="1.0"；projectContractVersion=1 |

使用 fullmatch 或等价完整匹配；拒绝末尾换行、空白、大小写、斜杠、点段、百分号编码、Unicode 混淆；不静默 lowercase、URL 解码或去空白。允许合法后缀内部连字符。不得因改名而重写原事件或创建新项目 UUID。

不新增 domainTemplate、projectDomain、payload.projectRef、project.list、projectDomainRouting、0009 项目分域迁移。不放宽 Creator/Worker 全局 domain 校验，不升级 buildContractVersion。若未来需要服务端独立项目策略，另立设计。

## 3. 当前基础与实施位置

S=`C:/Users/27846/my-chatgpt-skills`；R=`C:/Users/27846/my-chatgpt-mcp-v2`。以当前工作树为准，保护两仓库已有未提交改动。

已核验：S 最新 profile-aware-skill-creator 允许定义一个或多个可观察维度；原 capability 1.0 是固定 domain。现有 teaching subjectKey 为 `<projectId>:<unitId>`。R 当前本地 query.js 支持 interview/interview 的 project_summary 目录和 projectId 过滤；0008 身份表只在正式 session 接纳时产生记录。generic 投影的 summary 含活跃成员 evidenceRefs，event_activity 行保留原事件，用来解析活跃证据。读取原 observation 行不能直接当成仍生效事实。

以上是本地文件事实，不证明线上启用。本轮不读取个人画像，也不写真实事件。实施前重新查询 capabilities；interviewProjectSnapshots 的当前声明以当次真实响应为准。

## 4. 最小持久化：两个中性维度

本节是设计提出的实现选择。沿用 generic 1.0 已有字段，不扩展 envelope。只在目标 Skill 的 capability 中添加一个维度，不修改 Creator schema 或验证器。

| dimensionKey | subjectKey | 可记录事实 | outcome |
|---|---|---|---|
| learning-outline | `<projectId>:<unitId>` | 本轮确实讲过的入口、角色、顺序、状态、边界 | observed |
| project-binding | `<projectAlias>` | 用户明确确认“此别名属于这个项目 UUID 及来源依据” | observed |

project-binding 是中性元数据，不是学习成绩。confidence=high 只表示确认事实可定位。由项目学习 Skill 负责写入；模拟面试与复盘只读此映射。用户确认来源不可定位时，只在当前会话使用，不声称已跨会话保存。

绑定 observation 的 evidence 是 UTF-8 JSON 文本，最多2048字节，解析后严格只有下列五字段：

```json
{"bindingVersion":1,"projectAlias":"project-12306","projectId":"11111111-1111-4111-8111-111111111111","displayName":"12306","basis":{"kind":"source_learning","key":"confirmed-source:train-12306"}}
```

这是合成结构示例，不能写真实账户。projectAlias 必须等于 subjectKey；projectId 为 UUID；displayName 非空且不超过128字符；basis.kind 沿用 resume_claim/user_confirmed/source_learning，basis.key 非空且不超过256字符。拒绝未知字段、重复 JSON 键、非对象、缺失、类型错误或仅由模型猜出的确认。

sourceRef 使用可定位的 `project-confirmation:<conversationId>:<messageId>`。evidence 只承载该中性确认事实，不塞入源码、简历全文、录音、答案或额外文件。eventId/eventKey/requestId 首次提交后冻结；重试不换 ID。

首次绑定是独立命名事实，不伪装成“完成课程”。在次日回顾阶段，即便用户提到别名，也不生成绑定或其他事件；确需配置时在明确结束回顾后单独确认。

## 5. 解析、恢复与冲突

1. capabilities → 凭据身份 user.resolve → profile/backend-project-learning 分页读取。generic 读取不附加尚未支持的 projectId/rowKind 过滤。
2. 同一 projection 的所有页保持 revision，building=false 且 nextCursor=null 才算完整。限20页、每页limit=50、累计UTF-8 JSON响应≤5 MiB；超预算或 revision 变化重读仍失败时为 unresolved，不把半页结果当唯一映射。需再次重读时整次预算重置，最多重新开始一次；仍变化则暂停历史依赖操作。
3. 遍历 summary.observations 中全部 project-binding 成员，以各自 evidenceRefs 为活跃 eventKey 集合；从同 revision 的 event_activity 行定位原事件并解析同维度/subjectKey的 observation。不能只检查选中别名而漏掉同UUID的另一别名。已失效记录不能靠 observation 行重新复活；缺失引用返回 unresolved。
4. 相同别名的全部活跃绑定必须指向完全相同的五字段值；同 UUID 对应多个活跃别名或 basis 不一致也视为 conflict。本期不支持重命名、合并或多别名。不能采用“最后写入获胜”解决不同 UUID。
5. 解析唯一后，提纲按 UUID:unitId 精确筛选；面试读取 interview/interview，并传该 UUID 的 projectId。项目切换时清空上一项目选题上下文，保留各自只读缓存的用户、项目、revision 标记。

### 历史无绑定

先读凭据范围内 interview 的 project_summary 目录，再看旧 learning-outline 的严格 UUID:unitId 候选。目录为空不等于没项目：可能此前只听过课。展示最小框架、日期、sourceRef，让用户确认具体 UUID；不能按相似名、路径或旧源码位置自动归属。

旧提纲不重发、不改 domain/eventKey。用户确认后才追加绑定事实；正式 session 继续使用原 UUID/basis。孤立提纲没有 basis 时，先通过实际确认建立来源依据，后续 session 若服务器报告 project_identity_conflict，停止并核实，不换 UUID 掩盖。

通常只有历史完整可读、无可确认候选且用户确认新项目时才生成新 UUID；既有投影缺失/构建中/读取失败均为历史未知，不能据此自动新建。当前会话普通教学仍可继续。

首次使用的引导例外：capabilities和身份核对成功、历史查询明确返回projection_not_found、没有已知pending事件时，可说明“当前没有可读取的历史，不能据此证明从未记录过”，由用户明确要求创建一个独立新项目。只有该新建确认可定位时，才允许建立新UUID及绑定；这不是把未知推断成空历史。building、超时、分页不完整、身份错误或已有冲突不适用例外。用户要求“沿用之前项目”也不能走此分支。

### 一致性边界

本方案没有新增服务端唯一别名索引。两个客户端并发确认可能产生冲突，不能承诺原子唯一绑定。追加前重读并核验，projected 后完整读回；冲突或未确认投影时，不启动依赖该别名的正式读写。以后完整读取发现冲突则立即停止自动路由。

确认本轮写入已投影时，要求该 eventKey 可在所读 revision 的活跃证据中定位；不能仅凭“读到了相同别名”称本次完成。冲突修复由用户确认正确映射，对已读取错误绑定逐个 invalidate，保留不可变历史；回顾期间不修复。该流程可恢复冲突，但不等价于线性一致；要求严格多客户端唯一性时另立服务端方案。

## 6. 学习与面试共享证据

| 责任方 | 唯一负责内容 | 存储 |
|---|---|---|
| 项目学习 | 绑定确认、真实已讲提纲、学习后的真实作答 | 前两者 profile；作答 interview.session.completed |
| 模拟面试 | 从已确认简历项目和快照形成问题，保存实际首答 | interview.session.completed |
| 面试复盘 | 按同一 rubric 评价具体回答，追加/修订评价 | interview.review.completed |
| RDS | 不可变事件、派生快照、弱点状态 | 原有服务端合同 |

不把正式回答和评分复制进 generic profile；不在问题或 session DTO 内随意追加 projectAlias。别名解析是调用前上下文，正式合同只用原 projectId/basis。模拟面试/复盘通过合同协作，不依赖彼此私有提示词。

知识单元通过现有 unitId、questionKey、variantAxes 和 weaknessId 关联；questionKey 指向稳定考点，variantId 指向条件变化，不用换数字伪装迁移。先复用现有字段，不新建知识图谱或总掌握分。是否关闭弱点继续由服务端按独立作答、不同 session/变式/曝光组计算；教练不能手动声称关闭。

## 7. 教学与选题输出标准

学习模式：原创生活场景与适量幽默 → 可直接看见的时序图 → 按角色解释责任 → 实际调用链与绝对路径/核验起始行 → 最小关键代码及逐段详细中文注释 → 状态/失败分支/反例 → 可口述答案 → 底部一道追问并等待回答。图不可渲染时提供可显示的图片及责任表，不只给原始 Mermaid 文本。

注释解释输入、分支、状态、副作用、返回值和责任边界；区分现有逻辑、静态推断和建议修复。只借鉴小林coding的图解、代入、逐步推进方式，使用原创措辞，不复制文章。幽默不能挤掉源码证据。

学习可先给答案；formal mock 作答前不展示标准答案。学习后同题已曝光必须标记 answer_shown / exactAnswerSeenBefore=true；提示与补答追加，不覆盖首答。用户未回答则无 session；“不会”是有效真实回答。

面试以用户确认的简历项目为入口，联网检索详细内容，优先项目官方源码、技术官方文档；社区面经只作候选线索，说明发布日期、适用版本与证据局限。模型综合选择与该项目相关、能沿源码解释的问题。深度依次为链路、原因、反例/修复/验证、迁移/取舍；这是字节校招准备目标，不宣称内部题库或录用标准。

## 8. 次日回顾

开始当日新项目之前，按 Asia/Shanghai 昨日自然日，从真实提纲定位上一日主体框架，让用户口述入口、角色、主链路和关键边界。该段提问、回答、提示、评价、绑定、outline、attempt、review、报告附件全部零新增持久化；不计独立复测，也不能改名后补录。

回顾结束后才开展新教学。若用户要求正式专项，重新出一题，使用新的 attempt/session，不使用刚才的回顾回答。回顾优先级高于任何“顺便记录”的信号。

## 9. 实施范围与验收顺序

先打通 project-12306 一个完整闭环：确认项目 → 教学 → 真实首答 → 评价 → UUID快照读回 → 次日回顾零写入 → 新条件专项。再验证 project-pig-rpc 切换隔离。完整已认可教学样本与三张PNG随交接包提供，不仅交目录或提纲。

本期产品改动集中在 S/software-project-learning 的合同、capability、纯构造器、别名解析器和对应测试，以及模拟面试最小接线。R 默认不改代码/迁移；只做隔离测试证明既有 generic / interview 接口可承载。若实际证据显示缺能力，标为 blocked，另列最小差异提案，不能自行恢复斜杠方案。

使用最新 Creator 的三个画像工件并运行其 profile 校验；profile-binding 元数据不成为成绩。共享旧 runtime 文档如仍含账户注册说明，以本设计和最新 Creator 的“凭据绑定核对、不得注册或切换”为本次约束，作为基线差异报告，不扩散修改其他技能。

所有产品验收目前为 not_run。文档/夹具校验不代表插件已更新或线上可用。
