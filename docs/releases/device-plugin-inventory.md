# Device plugin inventory

本清单是发行包的冻结输入。构建脚本会读取当前提交中的源文件，计算每个入口的 `sourceSha`，再计算整体 `packageHash`；不从机器用户目录读取运行时数据。

| name | disposition | sourceSha | notes |
| --- | --- | --- | --- |
| account-gateway | add | generated | 只负责账户授权与 bindingContext |
| algorithm-learning | retain | generated | 个人内容调用统一 submit_event |
| backend-project-learning | retain | generated | 个人内容调用统一 submit_event |
| conducting-java-backend-mock-interviews | retain | generated | 个人内容调用统一 submit_event |
| reviewing-java-backend-interviews | retain | generated | 个人内容调用统一 submit_event |
| java-knowledge-based-on-resume-learn-skill | retain | generated | 个人内容调用统一 submit_event |
| software-project-learning | retain | generated | 非个人内容默认不增加授权依赖 |

构建输出必须包含：冻结清单版本、源码提交 SHA、每个 SKILL.md 的 SHA-256、运行时版本和最终 `packageHash`。包内不包含秘密、Outbox、运行时账户元数据或绝对用户路径。
