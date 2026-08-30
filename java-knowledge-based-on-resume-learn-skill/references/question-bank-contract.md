# 规范题库契约

题库关系：`简历声明 -> 知识点 -> 规范题目 -> 推荐回答链 -> 评分要点`。

题库通过 `submit_event` 提交 `resume-knowledge.question-bank-created` 事件，由 Worker 物化到 `users/<userId>/resume-knowledge/question-bank/snapshots/`。技能只负责生成，不负责存储。

## 知识域

题库必须覆盖简历涉及的后端知识域，包括但不限于：

- Java 基础、集合、并发与 JVM；
- Spring、Spring Boot、Spring Cloud 与 MyBatis；
- MySQL、事务、索引、锁与 MVCC；
- Redis、缓存、持久化、高可用与分布式锁；
- Kafka、RocketMQ、RabbitMQ 等 MQ；
- 微服务、RPC、网关、注册中心与配置中心；
- 分布式事务、一致性、幂等、限流与熔断；
- 网络、操作系统与 Linux；
- Elasticsearch、Docker、Kubernetes 等简历涉及的基础设施与中间件。

简历未涉及且无法强推断的知识域不进入题库。

## 题目字段

每道规范题至少保存：

| 字段 | 含义 |
| --- | --- |
| `questionKey` | 语义稳定的规范题标识 |
| `knowledgePointId` | 所属知识点 |
| `resumeVersion` | 生成该题目所依据的简历版本 |
| `evidence` | 证据级别：`explicit`、`strong-inference`、`unsupported` |
| `resumeEvidenceRefs` | 引用的简历声明 ID |
| `type` | `principle`（原理题）或 `scenario`（场景题） |
| `prompt` | 题面 |
| `answerChain` | 推荐回答链 |
| `scoringPoints` | 关键评分点 |
| `referenceAnswer` | 参考回答 |
| `conditional` | 强推断是否已使用条件式措辞 |
| `confirmed` | 强推断是否已被用户确认 |
| `masteryScore` | 当前题目掌握度 |
| `lastScoredLocalDate` | 最近计分日期 |

## questionKey 稳定性

`questionKey` 表示语义稳定的规范题，而不是当前措辞。仅改写表述不得产生新的 `questionKey`，从而绕过每日一次计分限制。

改写、润色或翻译题面都沿用原 `questionKey`；只有考察的语义发生变化时才生成新键。

## 展示边界

推荐回答链、评分点和参考回答保存在题库中，供用户作答后生成反馈。题单与题面只携带 `questionKey`、`slot`、`knowledgePointId`、`evidence`、`type` 与 `prompt`。
