# 联网题源与来源卡

联网只用于回答“这个岗位/方向最近出现过什么话题”，不用搜索摘要当技术答案。技术结论以项目源码、官方文档或可复现实验为准；摘要与官方冲突时以官方/源码校正，并把差异写进 `relevanceNote`。

## 来源卡字段

| 字段 | 约束 |
|---|---|
| `sourceId` | 稳定 ID；同一张卡复用后不再改名。 |
| `url` | 可公开访问的原帖地址；不写带 token、签名或私有链接。 |
| `title` | 原帖标题；不把标题润色成结论。 |
| `author` | 可得时填；不可得为 `null`。 |
| `publishedAt` | 发布时间（ISO-8601）；**日期不明必须为 `null`**，不得猜。 |
| `retrievedAt` | 实际检索时间，必填且带时区。 |
| `role` | 岗位或方向，例如 `Java 后端校招`。 |
| `recruitmentType` | 校招 / 实习 / 社招 / 转正等；不明为 `null`。 |
| `region` | 地区或批次；不明为 `null`。 |
| `evidenceLevel` | 线索强度，例如 `official_jd`、`candidate_report`、`aggregated_post`、`anonymous_claim`。公开帖子是个人自述，不保证真实。 |
| `originGroupId` | 原帖及其转载、翻译、摘编共用一个组；**同一组只算一条线索**。无法判定同源时给独立组，并在 `relevanceNote` 说明依据。 |
| `relevanceNote` | 与本项目/岗位的相关性、可转成什么条件变式；不得写用户私密信息。 |

```json
{
  "sourceId": "src-001",
  "url": "https://example.com/post/123",
  "title": "Java 后端校招面经：缓存与事务",
  "author": null,
  "publishedAt": null,
  "retrievedAt": "2026-10-24T12:00:00+08:00",
  "role": "Java 后端校招",
  "recruitmentType": "campus",
  "region": "CN",
  "evidenceLevel": "candidate_report",
  "originGroupId": "origin-123",
  "relevanceNote": "提到余票缓存回填与锁内二次检查，可转成条件变式；技术细节待源码核验"
}
```

## 计数与时效

- 同一 `originGroupId` 只计一条线索；跨多篇出现不等于统计概率，不得用转载数量制造“高频”“必考”。
- 优先近 12 个月、同批次/地区/方向的材料；不足时如实说明样本少或年代久，不把旧帖包装成当前趋势。
- 搜索摘要与官方文档冲突时，以源码或官方文档校正；不确定的结论不出题，或降级为“机制理解”并标注来源局限。
- 联网不可用或只有历史帖时，标记 `frequency=unknown`，改用已核验资料或原创条件题，并说明“非统计结论”。
- **不得编造出处**：没有可核验链接就不写 `url`/`author`/`publishedAt`；宁可少一张卡，也不伪造面经、公司或日期。

## 隐私与搜索词

- 搜索词只含公共技术、岗位方向和项目公开名称，例如 `Java 后端 校招 缓存 事务`。
- 不搜索、不记录：真实姓名、公司内部代号、未公开系统名、简历原文、私有 URL、账号或凭据、用户项目的私有路径。
- 用户提供的私密材料不进入搜索、来源卡或候选卡；公开信息与用户材料分开存放。

## 从来源卡到候选卡

- 一张来源卡可以产生 0–N 张候选卡，但技术答案必须先被源码或官方文档核验。
- 同一 `originGroupId` 的多张候选卡只保留一条线索，其余在计划里以 `duplicate_origin_group` 剔除。
- 候选卡用 `sourceRefs` 指向可核验材料；找不到核验材料时，不出“背结论”的题。

## 与选择器的关系

`build_question_plan` 按 `originGroupId` 去重，联网标记只影响说明与 `warnings`，不会把搜索摘要升级成标准答案。完整 mock 的来源配额见 [模拟面试协议](interview-protocol.md)；专项模式的约束见 [项目专项面试](project-targeted-interview.md)。
