# 简历驱动的 Java 后端八股学习技能设计

## 1. 背景与目标

在现有 `my-chatgpt-skills` 插件中新增
`java-knowledge-based-on-resume-learn-skill`。该技能从候选人简历出发，建立可追溯的
Java 后端知识地图、规范题库和人物掌握度快照，并支持用户自行创建的每日定时任务按薄弱点出题。

本设计同时统一插件的云端数据根路径、用户注册入口和写入协议，避免算法学习、模拟面试、面试复盘与新技能继续维护彼此分裂的身份和快照。

目标：

- 严格依据简历明示内容和可核实的项目强推断出题。
- 覆盖 Java 后端完整知识域，包括 Java/JVM、MySQL、Redis、MQ、Spring、微服务与简历涉及的中间件。
- 每题回答后给出结构化反馈、100 分制评分、推荐回答链和参考回答。
- 使用追加事件生成掌握度快照，按低分优先安排后续题目。
- 保证同一用户、同一自然日、同一稳定题目只接受第一次回答计分。
- 所有插件持久化数据只通过 `submit_event` MCP 提交。
- 所有新数据统一写入 `DriveRoot/my-chatGPT-skills/`。
- 对算法学习、模拟面试和面试复盘做全量规范化迁移，使有效技能说明、模板、Schema、辅助脚本与 Worker 实现遵守同一身份和目录契约。

非目标：

- 新技能不创建、更新或管理定时任务。
- 新技能不负责完整模拟面试；正式面试节奏和整场复盘继续由现有模拟面试技能负责。
- 不默认上传或保存简历原文件，只保存结构化声明、证据位置、版本号和文件指纹。
- 不把简历完全无依据的技术补入题库。
- 不直接移动、覆盖或删除旧 Drive 数据。

## 2. 已确认的产品边界

### 2.1 工作模式

新技能提供四种模式：

1. 简历初始化或更新：提取声明、生成知识地图和版本化题库。
2. 逐题学习：一次处理一道题的回答、反馈、评分和画像更新。
3. 每日练习：生成或读取当天固定题单，供用户自己的定时任务调用。
4. 掌握度查看：展示覆盖率、低分项、近期问题和下一轮优先内容。

### 2.2 与现有技能的分工

- 新技能拥有简历声明、知识点、规范题目、每日题单、单题反馈和简历八股掌握度。
- `conducting-java-backend-mock-interviews` 拥有正式面试节奏、连续追问和整场会话。
- `reviewing-java-backend-interviews` 拥有面试复盘和整场表现总结。
- 三者可以共享简历声明和薄弱点，但不重复承担完整模拟面试职责。

### 2.3 定时任务边界

用户自行创建独立定时任务。典型任务在每天 09:00（`Asia/Shanghai`）调用：

```text
使用 java-knowledge-based-on-resume-learn-skill，
为<姓名>生成今天的简历八股练习。
```

技能不读取、不创建、不修改任务调度配置。自然日由调用任务的时区确定，任务应显式提供时区。

## 3. 总体架构

采用“追加事件 + 派生快照”的架构。技能只负责理解、生成和调用 MCP；Cloud MCP Worker 是唯一 Drive 写入者。

```text
简历或用户回答
  -> 新技能生成结构化事件
  -> submit_event MCP
  -> Worker 校验并解析/注册用户
  -> Worker 追加原始事件
  -> Worker 物化简历、题库、题单或画像快照
  -> MCP 返回事件与物化状态
```

任何技能不得直接调用 Google Drive 创建文件夹、上传 JSON、覆盖快照、移动文件或写入旧目录。Google Drive 仅作为最终存储层；`submit_event` MCP 是所有插件持久化数据的唯一提交入口。

读取可以使用现有的只读 MCP 能力。写入失败时不得回退到旧路径或直接调用 Drive。

## 4. 统一身份与注册

### 4.1 姓名解析

插件只服务少量已知用户，不引入复杂鉴权。姓名是用户解析入口，每个不同用户拥有独立且不可变的 `userId`。

姓名标准化包括：

- Unicode NFKC 标准化；
- 去除首尾空白；
- 统一全角和半角形式。

除这些机械标准化外，不根据昵称、相似拼写或推断自动合并用户。

### 4.2 注册行为

`submit_event` 同时支持显式注册与首次业务事件自动注册：

1. 请求提供标准化前的 `displayName`。
2. Worker 根据 `nameKey` 查找全局注册表。
3. 若命中唯一用户，返回现有 `userId`。
4. 若不存在，生成稳定的新 `userId`，创建注册文件、身份文件和用户文件夹。
5. 若发生无法消解的同名冲突，停止并要求人工选择，不自动合并。

重复注册同一标准化姓名必须幂等，返回相同 `userId`。注册成功后，Worker 可以继续处理同一调用中的业务事件。

注册至少物化：

```text
DriveRoot/my-chatGPT-skills/
├── user-registry/registration-<userId>.json
└── users/<userId>/
    └── identity.json
```

注册操作允许 Worker 创建用户文件夹。领域子目录按首次物化需要创建，不要求预先建立空目录。

## 5. 统一存储布局

```text
DriveRoot/my-chatGPT-skills/
├── user-registry/
│   └── registration-<userId>.json
└── users/<userId>/
    ├── identity.json
    ├── algorithm/
    │   ├── events/
    │   ├── profile/snapshots/
    │   └── plans/daily/
    ├── interview/
    │   ├── events/
    │   └── profile/snapshots/
    └── resume-knowledge/
        ├── sources/resume/snapshots/
        ├── question-bank/snapshots/
        ├── events/
        ├── profile/snapshots/
        └── plans/daily/
```

所有新写入必须位于该根路径。领域使用统一的 `events -> profile/snapshots -> plans/daily` 形状；只在领域确实需要时增加来源或题库目录。

## 6. `submit_event` 写入契约

新领域扩展现有事件信封，不替换已有公共字段。每个事件必须具备：

- schema 版本；
- 领域；显式注册和迁移使用 `system`，简历学习业务使用 `resume-knowledge`；
- 事件类型；
- 唯一事件 ID；
- 幂等键；
- 发生时间；
- 用户姓名，以及解析后由 Worker 返回的 `userId`；
- 与事件类型匹配的结构化 payload。

事件类型：

```text
system.user-registered
system.legacy-migration-requested
algorithm.learning.completed
algorithm.daily-plan-created
interview.session.completed
interview.review.completed
resume-knowledge.resume-ingested
resume-knowledge.claim-confirmed
resume-knowledge.claim-rejected
resume-knowledge.question-bank-created
resume-knowledge.daily-plan-created
resume-knowledge.answer-scored
```

注册可以通过 `system.user-registered` 显式提交，也可以由任一业务事件的解析阶段自动触发。迁移只接受 `system.legacy-migration-requested`。无论哪种方式，注册文件、用户目录和迁移结果只能由 Worker 在 `submit_event` 调用内物化。

物化规则：

- `user-registered`：幂等创建或返回全局用户注册与用户目录。
- `legacy-migration-requested`：执行 dry-run 或经过确认的非破坏性复制。
- `algorithm.learning.completed`：追加算法学习事件并物化算法画像快照。
- `algorithm.daily-plan-created`：保存不可变的算法当日题单。
- `interview.session.completed`：追加模拟或真实面试会话事件，不直接修改画像。
- `interview.review.completed`：追加面试复盘事件并物化面试画像快照。
- `resume-ingested`：保存结构化简历声明快照和文件指纹。
- `claim-confirmed` / `claim-rejected`：更新证据状态，供下一版题库使用。
- `question-bank-created`：保存与简历版本绑定的规范题库快照。
- `daily-plan-created`：保存不可变的当日题单。
- `answer-scored`：保存首次有效评分事件，运行 reducer 并生成新人物快照。

当天重复回答不调用 `submit_event`，只在当前会话生成反馈。

如果原始事件已存在但投影物化失败，同一幂等键的重试不得重复追加事件；Worker 应识别已有事件并补做缺失投影。

## 7. 简历版本与证据模型

每次处理新简历时创建新的 `resumeVersion`，保存：

- 结构化声明；
- 声明之间的项目归属关系；
- 技术标签；
- 原文中的证据位置；
- 文件指纹；
- 激活时间。

历史题目、题单和评分继续绑定当时的 `resumeVersion`。新简历不覆盖旧版本。

证据分三级：

| 证据级别 | 允许行为 |
|---|---|
| 简历明示 | 直接建立知识点并出题 |
| 项目强推断 | 条件式提问，或先请用户确认 |
| 无依据 | 禁止进入题库 |

用户确认强推断后追加 `claim-confirmed`；用户否认后追加 `claim-rejected`。被否认的声明不得再次被当作项目事实出题。

简历明确列出某技术时，可以考察该技术的常见核心八股，不局限于简历原句；但不得把常见方案说成用户在项目中真实使用过的方案。

例如简历写了 Redis：

- 可以直接询问缓存穿透、击穿、雪崩、持久化和分布式锁；
- 可以条件式询问“如果项目需要防止重复执行，你会如何利用 Redis”；
- 不能断言用户实际使用了 Redisson 看门狗。

没有有效简历快照时，技能必须停止出题并要求用户先提供简历，不得退化为通用 Java 八股。

## 8. 知识地图与规范题库

题库关系：

```text
简历声明 -> 知识点 -> 规范题目 -> 推荐回答链 -> 评分要点
```

知识域包括但不限于：

- Java 基础、集合、并发和 JVM；
- Spring、Spring Boot、Spring Cloud 和 MyBatis；
- MySQL、事务、索引、锁和 MVCC；
- Redis、缓存、持久化、高可用和分布式锁；
- Kafka、RocketMQ、RabbitMQ 等消息队列；
- 微服务、RPC、网关、注册中心和配置中心；
- 分布式事务、一致性、幂等、限流和熔断；
- 网络、操作系统和 Linux；
- Elasticsearch、Docker、Kubernetes 等简历涉及的基础设施。

每道规范题至少保存：

- 稳定的 `questionKey`；
- `knowledgePointId`；
- `resumeVersion`；
- 简历证据引用与证据级别；
- 题目类型和题面；
- 推荐回答链；
- 关键评分点；
- 参考回答；
- 当前题目掌握度和最近计分日期。

`questionKey` 表示语义稳定的规范题，而不是当前措辞。仅改变表述不得产生新的题目键，从而绕过每日一次计分限制。

推荐回答链、评分点和参考回答不得随每日题单提前展示，只能在用户作答后用于反馈。

## 9. 每日题单

用户自己的定时任务调用每日模式后，技能：

1. 按姓名解析或创建用户。
2. 检查有效简历和题库。
3. 检查当日题单是否已经存在。
4. 已存在则原样返回；不存在则选择题目并通过 `daily-plan-created` 提交。
5. 一次返回全部题面和必要的来源标签，但不返回答案或评分点。

每日默认选择五题：

1. 两道当前题目掌握度最低的题；
2. 一道尚未考察的简历明示题；
3. 一道项目场景追问题；
4. 一道历史低分复测题。

选择必须去重。弱项排序依次考虑：

```text
低题目掌握度
-> 低知识点掌握度
-> 更久未复测
-> 更高简历相关度
```

未考题使用专门的新题位置，不按 0 分混入低分排序。如果简历证据不足以安全提供五个不同题目，则返回更少题目并解释原因，禁止使用无依据的通用八股补齐。

当日题单首次创建后不可变。当天上传的新简历从下一个尚未创建题单的日期生效。

## 10. 单题反馈与评分

每道题回答后固定返回：

1. 总分和四个维度分数；
2. 已回答正确的内容；
3. 错误、遗漏和表达问题；
4. 推荐回答链；
5. 面试可直接使用的参考回答；
6. 掌握度变化和保存状态。

评分采用 100 分制：

| 维度 | 权重 |
|---|---:|
| 技术正确性 | 40 |
| 关键点完整性 | 25 |
| 回答链路与层次 | 20 |
| 简历场景结合度 | 15 |

回答链按题型自适应：

```text
场景题：业务场景 -> 核心问题 -> 原理 -> 方案 -> 实现细节 -> 风险与替代方案
原理题：定义 -> 核心机制 -> 关键流程 -> 示例 -> 边界与常见误区
```

例如分布式锁题可以遵循：

```text
并发场景
-> 竞态、超卖或重复执行
-> 单机锁无法覆盖多实例
-> Redis SET key value NX EX
-> 唯一 value 标识锁持有者
-> Lua 脚本原子校验并释放
-> 过期、续期和锁失效问题
-> Redisson 看门狗、主从一致性与 fencing token
```

回答问题归类包括：技术事实错误、关键点遗漏、回答链断裂、项目场景结合不足、把推测说成实际经历，以及表达冗余或缺少结论。

## 11. 每日一次计分与掌握度

计分幂等键：

```text
userId + localDate + questionKey
```

- 当天第一次回答：生成反馈，提交 `answer-scored`，更新掌握度并生成快照。
- 当天再次回答：仍生成完整反馈，但明确提示今日已经计分；不提交事件，不更新画像。
- 次日同题再次出现：生成新的日期级幂等键，允许重新计分。

题目掌握度：

```text
首次：masteryScore = 本次得分
后续不同日期：newMasteryScore = 0.6 * 本次得分 + 0.4 * 原掌握度
```

知识点掌握度是该知识点下所有已考规范题当前掌握度的平均值。未考题保持 `untested`，不按 0 分计入平均值；同时单独保存覆盖率，避免少量高分掩盖大量未考题。

## 12. 人物快照

每个首次有效 `answer-scored` 事件后，Worker 运行 reducer 并生成新的不可变快照。快照至少包含：

- `resumeVersion`；
- `headEventId`；
- 知识点掌握度；
- 题目掌握度；
- 题库覆盖率；
- 近期错误和回答问题；
- 按优先级排序的薄弱点；
- 下一轮推荐复习内容；
- `sourceEventKeys`。

快照是事件的派生结果，不接受技能直接上传或覆盖。任何快照都应可以从原始事件重建。

## 13. 渐进迁移

迁移期间：

- 读取顺序为新路径优先、旧路径回退；
- 所有新写入只进入统一新路径；
- 旧目录保持只读；
- 不移动、不覆盖、不删除旧数据。

迁移由专用迁移事件通过 `submit_event` 触发，Worker 执行：

1. 根据标准化姓名关联旧用户。
2. dry-run 生成待复制清单和冲突报告。
3. 获得执行条件后复制并校验内容哈希。
4. 相同事件跳过；同键不同内容立即停止并报告。
5. 保留可审计的迁移结果，不修改旧对象。

技能不得为了迁移直接调用 Drive 写工具。

## 14. 异常处理

- 无简历：停止出题并提示上传简历。
- 证据不足：减少题目数量，不用通用题补齐。
- 同名冲突：停止并要求人工选择。
- `submit_event` 整体失败：可以返回反馈，但必须明确说明评分未保存。
- 原始事件成功、投影失败：返回部分成功状态；同一幂等键重试补做投影。
- 新路径不可写：停止写入，不回退旧路径。
- 当日题单已存在：返回原题单，不重新随机生成。
- 当天重复回答：只反馈，不持久化第二次回答。
- 新简历在当日题单后到达：保持当日题单不变，后续日期使用新版本。

## 15. 实现范围

### 15.1 新技能

```text
java-knowledge-based-on-resume-learn-skill/
├── SKILL.md
├── agents/openai.yaml
└── references/
    ├── resume-evidence-policy.md
    ├── question-bank-contract.md
    ├── feedback-scoring-contract.md
    ├── profile-storage-contract.md
    └── daily-task-prompt-template.md
```

### 15.2 Cloud MCP

- 增加统一路径构造与姓名注册能力。
- 扩展 `submit_event` 的 `resume-knowledge` 事件校验和分发。
- 增加简历、题库、题单和画像的物化逻辑。
- 增加评分幂等检查和人物画像 reducer。
- 增加新路径优先、旧路径回退的只读适配。
- 通过迁移事件支持 dry-run 和非破坏性复制。

### 15.3 现有技能全量规范化（必须实现）

本项不是文档整理，而是现有持久化能力的行为迁移。算法学习、模拟面试、面试复盘及 Cloud MCP 必须同时切换，不能出现“Skill 声明新路径、Worker 仍写旧路径”的半迁移状态。

共享要求：

- `AGENTS.md`、三个 `SKILL.md`、当前有效 reference、Schema、辅助脚本和 Cloud MCP 实现统一使用 `DriveRoot/my-chatGPT-skills/`。
- 三个技能都按标准化姓名解析全局注册；不存在时允许在 `submit_event` 调用内创建稳定独立的 `userId`，不再维护 namespace 独立身份。
- 所有云端业务写入只能通过 `submit_event`；技能、模板和辅助脚本不得直接创建、更新、移动或删除 Drive 文件。
- 旧路径只允许出现在明确标注为“legacy read-only”的适配器、迁移说明、迁移测试或历史设计文档中；不得作为当前写入目标、每日任务输入或恢复回退目标。

`algorithm-learning`：

- 事件统一物化到 `users/<userId>/algorithm/events/`。
- 画像统一物化到 `users/<userId>/algorithm/profile/snapshots/`。
- 每日题单统一物化到 `users/<userId>/algorithm/plans/daily/`。
- 删除当前契约中对 `algorithm/users/`、`practice/`、`profile/current`、`profile/history`、JSONL 事件日志和直接 Drive 写入的有效依赖。
- Cloud MCP 在保存 `algorithm.learning.completed` 后真实重建算法画像快照，补齐当前“只写事件、不生成快照”的行为缺口。

`conducting-java-backend-mock-interviews`：

- 模拟面试会话事件统一物化到 `users/<userId>/interview/events/`。
- 继续只负责会话事件，不直接生成画像快照；本地 `outputs/interview/<userId>/` 副本仍是非画像派生文件。
- 删除 CandidateIndex、`candidate_id` 和候选人根目录作为运行时身份或云端写入契约的有效说明。

`reviewing-java-backend-interviews`：

- 复盘事件统一物化到 `users/<userId>/interview/events/`。
- 画像快照统一物化到 `users/<userId>/interview/profile/snapshots/`。
- 删除 `system/candidate_index.json`、`candidates/<candidate_id>/`、`profile/current_profile.json`、原始 transcript/报告上传等旧运行时写入流程；报告只保留本地派生输出。
- 复盘继续消费会话事件并生成确定性画像变化，但持久化和快照物化全部由 Worker 完成。

`backend-project-learning` 当前没有人物画像或云端持久化功能，不为其创建空领域目录。如果未来新增持久化，必须复用全局注册和 `submit_event`，不得另建身份或根目录。

Cloud MCP：

- 将现有 namespace 目录构造改为统一插件根、全局注册和用户领域目录构造。
- 为算法、面试和简历知识三个领域提供统一的追加事件、幂等、读回校验和快照物化骨架。
- 保留新路径优先、旧路径回退的只读适配；任何写入失败都不得转写旧 namespace 目录。
- 对原始事件成功但投影失败的调用返回可重试状态，并用相同幂等键补做投影。

## 16. 验证与验收

### 16.1 Cloud MCP 单元测试

- 姓名标准化和幂等注册。
- 不同姓名生成独立 `userId`。
- 统一路径构造。
- 每种事件的 schema 校验。
- 同日同题幂等拒绝第二次评分。
- 次日同题允许再次评分。
- EWMA 掌握度计算。
- 知识点平均分与覆盖率计算。
- 每日题单选择、去重和稳定复用。
- 原始事件存在时补做失败投影。
- 旧路径只读回退和新路径单写。
- 迁移 dry-run、哈希校验和冲突停止。

### 16.2 技能行为测试

- 无简历时不会生成通用题。
- 简历明示 Redis/MySQL/MQ 时能扩展核心八股。
- 不会把 Redisson 等常见方案冒充为用户实际项目事实。
- 强推断使用条件式措辞并能处理确认或否认。
- 每题反馈包含分数、问题、回答链、参考答案和保存状态。
- 当天重复回答仍反馈但不再次提交事件。
- 每日模式优先低分，同时保留一个未考新题位置。
- 证据不足时少出题而不是越界补题。

新技能先运行无技能基线场景，再运行加载技能后的相同场景，验证证据边界、反馈形状和持久化规则确实改变了行为。

### 16.3 交付门槛

- 技能通过 `quick_validate.py`。
- Cloud MCP 全部单元与集成测试通过。
- 行为测试覆盖关键失败模式。
- 路径文档与 Worker 实现一致。
- Git 差异中不存在旧路径的新写入说明。
- 仓库级契约测试证明算法、模拟面试、面试复盘和简历八股都使用同一插件根、全局注册与 `submit_event`。
- 旧路径扫描只允许命中 legacy 适配器、迁移测试和带有明确废弃标记的历史文档。
- 运行时集成测试证明算法事件、面试会话、面试复盘与简历答题分别落入规范化目录，且不会创建 namespace 级 `user-registry/` 或 `users/`。
- 未执行任何破坏性 Drive 操作。

达到以上门槛后，才提交并推送完整实现。

## 16. 实现命名补充（实现期决定）

第 10 节的评分维度只给出了中文名与权重，未规定事件中使用的英文字段名。为了保持 JSON 事件可校验，实现采用如下机械转写，并在 `cloud-mcp/src/resume-knowledge-model.js` 的 `SCORE_DIMENSIONS` 中集中冻结权重，改名只需改一处：

| 中文维度 | 事件字段名 | 权重 |
| --- | --- | --- |
| 技术正确性 | `correctness` | 40 |
| 关键点完整性 | `completeness` | 25 |
| 回答链路与层次 | `structure` | 20 |
| 简历场景结合度 | `resumeRelevance` | 15 |

`answer-scored` 事件的 `scores` 只接受这四个字段，每个分数不得为负且不得超过该维度权重，四者之和必须等于 `total`。

同理，`resume-knowledge.*` 系列事件中未在第 6 节逐一列出的字段按以下约定命名：`resumeVersion`、`fingerprint`、`questionKey`、`masteryScore`、`localDate`、`planId`、`slot`，以及题目上的 `knowledgePointId`。证据等级字段名是 `evidence`，取值为 `explicit`、`strong-inference`（同时接受 `strong_inference`）或 `unsupported`；题型字段名是 `type`，取值为 `scenario` 或 `principle`。

`questionKey` 必须在语义上稳定，不得随题面措辞或顺序变化而改变，否则跨日掌握度无法累积。`rejected` 不是简历证据等级，而是用户否认某条声明后该声明进入的状态，字段名是 `status`。

本补充只固化已实现的命名，不引入新的行为要求。若后续要改用其它字段名，应在此处同步修订。
