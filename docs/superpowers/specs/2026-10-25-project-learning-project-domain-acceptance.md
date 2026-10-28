> **已被 v3 取代，历史参考，不执行本文件任务。** 用户选择固定 domain＋稳定项目 ID，入口名为 `project-12306`，前缀 `project-`。以下旧斜杠分域、Creator1.1、projectContractVersion2及迁移方案撤销。请改读 [2026-10-25-project-learning-project-alias-acceptance.md](2026-10-25-project-learning-project-alias-acceptance.md)。

# project/12306 分域：验收与完整示例

日期2026-10-25。本文28个产品case均为not_run；下文对话、身份、分数和预期结果都是合成示例，不发送个人RDS。配套[设计](2026-10-25-project-learning-project-domain-design.md)和[执行计划](../plans/2026-10-25-project-learning-project-domain-plan.md)。

## 一、28项实施验收

每项交回caseId/status/inputVersion/command或trace/exitCode/evidencePath/limitation。P0阻塞整体验收；P1缺口也须明确说明。关键词检查不代替实际行为演练，静态JSON可解析不代表协议可用。

| ID | 级别 | 输入或场景 | 预期结果 | 责任任务 |
|---|---|---|---|---|
| D01 | P0 | 选择12306、pig-rpc | 实际domain分别project/12306、project/pig-rpc；不是显示名替换 | PD2/PD5 |
| D02 | P0 | slug1/56/57字符、空、首尾-、多级、编码和Unicode | 只接受精确受限语法，不做静默转义/大小写修正 | PD1/PD2 |
| D03 | P0 | 原flat domain与保留字 | 原规则及拒绝行为保持，旧数据可读 | PD2 |
| D04 | P0 | sourceSkill或dimensionKey带slash | 仍拒绝；不把全局SAFE_ID放宽 | PD1/PD2 |
| D05 | P0 | namespace=project/12306，或domain作为Drive路径 | 拒绝错误namespace，不创建远端目录/上传原文件 | PD2/PD4/PD6 |
| C01 | P0 | 原1.0静态capability | 原schema字节不变且原技能继续通过 | PD1 |
| C02 | P0 | 1.1项目模板分别解析12306/pig-rpc | 得到具体domain；只接受固定project/{projectSlug} | PD1/PD5 |
| C03 | P0 | 混写domain/domainTemplate、未知模板或版本 | schema与手写校验均拒绝 | PD1 |
| C04 | P0 | JS/Python/Creator同一正负矩阵 | 解析和拒绝一致，模板字面量不上wire | PD1/PD2 |
| B01 | P0 | 先讲课写提纲，后第一次答题 | 首条真实提纲绑定UUID；后续session复用 | PD3/PD6 |
| B02 | P0 | 旧目录UUID但project_domain=NULL | 确认后补绑，不改UUID、不复制历史 | PD3/PD5 |
| B03 | P0 | 旧提纲有UUID而目录为空 | 只读展示原sourceRef候选；确认后首个新事实绑定；未确认不造UUID/不保存 | PD5 |
| B04 | P0 | 并发同域不同UUID/同UUID不同域/basis冲突 | 原子拒绝冲突，事件和目录无半提交 | PD3 |
| B05 | P0 | 两用户同名domain、尝试越权引用 | 各自独立，凭据范围之外拒绝且无原文泄漏 | PD3/PD4 |
| B06 | P0 | 原请求重试/alias，或旧v1新建目录项 | replay不重复加revision；实际目录变更必更新revision | PD3 |
| Q01 | P0 | project.list全目录/精确域/未绑定旧项/超限 | 精确字段，limit≤50、响应≤256KiB，允许旧项domain=null | PD4 |
| Q02 | P0 | cursor换用户、domain、operation、过期 | scope mismatch或过期拒绝，不能混页 | PD4 |
| Q03 | P0 | 目录分页途中补绑/新建 | directory_changed并重读；不混不同revision | PD3/PD4 |
| Q04 | P0 | 纯读取与跨domain投影cursor | 0 Outbox/业务写入；不同projectionName游标不混用 | PD4 |
| V01 | P0 | v1/v2 session+review及归档回放 | 旧v1保持，新v2不被===1分支忽略，继承源版本 | PD2/PD6 |
| V02 | P0 | 混合mock含12306和RPC两题 | 每题项目路由独立；session知识domain不被替换 | PD2/PD5 |
| V03 | P0 | 新域归档与已接纳事件后关闭feature | artifactId命名不变；后台处理继续；原容量与build预算不放宽 | PD3/PD6 |
| L01 | P1 | 请求“今天学余票，先给答案” | 原创场景、可见时序图、详细源码、边界、口述答案、末尾一道题 | PD5 |
| L02 | P0 | 没有用户回答、看过答案、提示补答 | 未答不造session；首答保留；辅助完成不算独立通过 | PD5 |
| L03 | P0 | 次日开始RPC前回顾昨日12306 | 跨域找到真实提纲；回顾问答/提示/反馈/outline全部0写 | PD4/PD5 |
| L04 | P0 | feature缺失/配置关闭/身份不符/投影未知 | 不写新域、不偷写旧域、不换账户；未知不当零分 | PD4/PD5 |
| L05 | P0 | 新旧提纲衔接及历史修订 | 只读旧事实，不改旧domain/eventKey、不重发、显示有来源 | PD5/PD6 |
| P01 | P0 | 交接报告称已完成/上线 | 分开文档QA、本地实现、回归、在线能力；未运行保留not_run | PD6 |

## 二、输出基准：教学正文保持完整

完整教学正文使用[已认可的余票展示样本](../../../software-project-learning/references/examples/ticket-query-rds-complete-dialogue.md)，交接包同时包含该MD及三张原PNG，不只提供目录。真实授课须重新核验目标源码、路径、行号；附带旧样本只复用教学动作，不能当作2026-10-25新做的并发实验或个人经历。

以下是新分域行为的完整合成对话。它接在完整教学正文之前/之后，验证不是只换一行domain。

### 场景A：已有旧提纲，但没有正式作答目录

**学员（合成输入）：** 我以前学过12306，今天从余票展示继续，domain就用project/12306。

**教练内部只读步骤：** capabilities→凭据身份核对→project.list精确查域。目录没有对应项目，但不能据此新造UUID；继续只读旧backend-project-learning提纲，找到候选UUID U1，原sourceRef指向旧课程消息，框架为“候选车次→价格/余票→缺失回源→返回Map”。

**教练：** 找到一份旧学习记录，内容是余票查询与Loader返回责任，项目标识为U1。它还没有绑定新域。确认是这份记录后，我会沿用U1接到project/12306，避免把同一个项目分成两本账。

**学员（合成）：** 是这份，沿用原记录。

此时只是确认绑定意图，不制造“用户又完成了一节课”的事件，也不重发旧提纲。等首条真实新提纲或正式作答产生时，由接纳事务建立绑定。

### 场景B：讲解、底部追问、保存真实作答

**教练讲授：** 使用同包完整余票样本：先展示三张可见时序图，再看Service的HGET/Optional、Loader的锁内二次检查和局部Map、数据库统计条件，最后用A回填5、B二次命中却返回空Map的反例说明责任。源码、现有逻辑和修复建议分别标注。

这像共享电子屏与前台便签：电子屏已经显示5，不代表B手里的便签自动写上了5。比喻之后仍须沿真实代码证明，不能用段子代替分支分析。

**教练（真实运行到此等待）：** B等待锁后二次检查命中5，请沿“B自己的Map→load返回值→外层quantity”说明当前实现显示多少，最小修复在哪个分支。

此时已讲授提纲可写profile/project/12306，outcome=observed、subjectKey=U1:unit-query，payload带projectRef。未回答前不构造session、不评掌握。

**学员（合成）：** B没有进入填Map的分支，自己的Map还是空的，最后外层按0兜底。最小修复是在锁内二次命中分支，把当前席别的缓存数量带回本次返回结果，不能只保证Redis已经有值。

**教练反馈：** 返回路径说清楚了。由于刚才已经看过同题解析，本次记录实际回答，但标记exactAnswerSeenBefore=true，不能当作一次独立复测。后续会换一个未讲过答案的条件来检验迁移。

**合成写入轨迹：**

| 实际事实 | namespace/路由 | 标识与owner |
|---|---|---|
| 已讲提纲 | profile，payload.domain=project/12306 | projectRef.projectId=U1；学习Skill |
| 正式原答 | interview，session.projectContractVersion=2 | Question.projectEvidence.project={projectId:U1,projectDomain:project/12306,...}；学习Skill |
| 对原答的评价 | interview，review继承版本2 | sourceSessionEventId指向原session；复盘Skill |

回执例（只是状态表达标准，不是真实本轮结果）：若只有D1回执，说“D1已接收，快照投影与Drive归档待确认”；不要直接说“Drive已保存”。快照由服务端计算，教练不上传snapshot JSON。

### 场景C：跨项目次日开场，不计快照

**合成次日输入（不代表现实已经过了一天）：** 今天开始RPC，使用project/pig-rpc。

**教练内部只读步骤：** project.list读取凭据用户目录，分别读取已绑定域提纲及必要的旧域兼容视图，按Asia/Shanghai昨日日期定位到12306框架。每个投影独立分页，遇revision变化重读。

**教练：** 开RPC之前，先用一分钟串一下昨天的余票展示：谁找候选车次、谁给数量、缺失时谁回源、最后谁负责把结果交回来？这段是把地图摊开，不计分、不写快照。

**学员（合成）：** Controller交给V1 Service，Service校验、找候选车次，再装配价格和余票。余票缺失走Loader，加锁再查，必要时统计回填；锁只能减少重复回源，命中值还要进入本次返回结果。展示余票不是购票预占。

**教练：** 主体接上了。今天进入RPC也沿着“谁发起、谁等待、谁完成返回”看，不让Future变成“将来再说”。接下来才开始今天的新链路。

本段远端写入=0；新增attempt=0；新增review=0；新增outline=0。之后真的讲完RPC新单元，才向project/pig-rpc写该单元的中性提纲。

### 场景D：指定单项目做变式，保持旧快照

**学员（合成）：** 先不学RPC了，只从project/12306快照换个条件考我。

**教练内部步骤：** project.list精确取得U1→interview/interview按U1读快照→查看原题已曝光、原回答与薄弱点→结合已确认简历项目及可核验资料形成候选。这里已由用户明确启动正式专项，不能沿用回顾题当attempt。

**教练：** 假设数据库已经统计得5，缓存回填调用却超时。你如何决定当前响应，并验证是“没写入”还是“写成了但回执丢失”？先说明业务允许的失败策略，再给观测方案。

**学员（合成）：** 已得到的统计结果和缓存副作用分开。如果业务允许回填失败继续展示，就保留5并记录回填失败；否则返回明确错误，不能伪装0张票。客户端超时不能证明没写入，关联车次区间席别、调用时间和链路日志核对。再次读到5也不能证明就是本请求写的，还可能有并发请求，因此需要受控故障验证。这里只是展示缓存，不应凭超时去补偿购票库存。

**教练（复盘阶段）：** 这次能区分主结果、副作用和未知结果。保留新attempt与来源，复盘Skill提交新评价，服务端更新U1的项目快照；原回答继续保留。是否算独立通过要结合本题答案是否提前展示、提示和曝光组，不由一个高分直接关闭弱点。

project/pig-rpc的问答和提纲不被混入本次选题。若缺projectDomainRouting或interviewProjectSnapshots，说明暂不能进行有可靠历史依据的专项；可继续普通讲解，不伪造已读取或同步成功。

## 三、机器工件与边界

交接包examples/profile-capability-v1.1.example.json是**拟议静态合同**的完整示例，不是当前Creator已经接受的文件。examples/project-domain-fixtures.json提供域正负矩阵、两项目的projectRef、提纲envelope和目录响应；外层fixtureOnly=true，禁止拆出后写个人RDS。

旧样本、本轮合成对话、静态校验probe、未来集成测试四者分开报告。只有DeepSeek交回实际改动和可复现证据后，才能进行实现验收；本轮不创建插件代码框架，也不替用户提交。
