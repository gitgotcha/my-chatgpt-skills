# 项目专项面试（project_targeted）

用户只想练一个已确认或已学习过的项目时使用本模式。它与完整 mock 并列，不替代完整 mock 的配比与 40% 弱点上限；完整 mock 的规则见 [模拟面试协议](interview-protocol.md)。

## 硬约束

1. **全部问题必须能回到选中项目**：每题保存可读项目路由、`sourceRefs`、`questionKey`、`variantId` 等；没有项目定位或源码/设计依据的题不得进入本场。内部存储 nodeId 不属于面试题字段。
2. **允许一题基础机制**：为解释项目链路所必需的最小背景机制（例如缓存回填、锁内二次检查、写超时结果未知），全场最多一题，仍须挂在该项目上下文并给出源码或官方文档 `sourceRefs`；第二道基础机制题应换一场，或改成项目内的条件变式。
3. **不混其它项目弱点**：只读选中项目的 `学习快照.json` 和该项目的已确认简历声明。其它项目的弱点即使刚更新也不选，也不拿“通用高频八股”凑数。
4. **不参与完整 mock 的 40% 上限**：专项可以全部是该项目弱点复测；完整 mock 仍保持弱点题不超过总题数 40%。两套规则互不影响，同一场只应用其中一套。
5. **默认 L2 起步，按表现走向 L1/L3/L4**：L2 机制 → 用户卡在链路事实时回退 L1 → 有作答证据后进入 L3 反例与修复 → 再谈 L4 迁移与取舍。不因候选卡写得深就跳级；不宣称公司内部标准、今年必考率或录用线。
6. **一次只问一道**：可以连续追问，但不把下一题或本题答案一起抛出。
7. **作答前不泄答案**：不展示完整参考答案、评分或本题结论；用户说“不会”时保留原回答，最多一次启发式追问，仍不会再继续下一题。

## 入口解析（project- 别名）

用户说“只考 project-12306 的快照”时，按 RDS-JBryon 可读路径 `project/12306` 读取。路径路由契约见[项目快照契约](../../software-project-learning/references/rds-jbryon-runtime.md)；不做 UUID alias binding。

- 路径不存在或匹配不唯一时，不启动依赖历史快照的专项；说明问题并询问正确路由。用户同意后可改做明确标记的通用 mock。
- 只有 `snapshot.read` 成功返回当前快照时，才称本场基于该项目快照。
- 旧的 `project_question_plan` UUID/binding 辅助器不参与 RDS-JBryon 路由；选题仅限本文件描述的快照与项目证据。
- 切换项目时清空上一场的候选与弱点上下文；不同项目的快照、题目和缓存不能混用。

## 选题输入

- 已确认的简历项目声明；没有确认声明时标明“非简历定制”，不造经历。
- 选中项目快照：已考 `questionKey`/变式、明确记录的待复习点、最近辅助程度及原答时间线。
- 候选卡：`candidateId`、`projectId`、`source`、`questionKey`、`variantId`、`variantAxes`、`level`、`weaknessId`、`basicMechanism`、`originGroupId`、`sourceRefs`。
- 联网线索只回答“出现过什么话题”，来源卡字段与计数规则见 [联网题源与来源卡](web-question-sourcing.md)；技术结论以源码或官方文档为准。

## 变式与去重

- 换数字、换人名、换项目名不产生新 `variantId`；只有改变故障模型或条件（例如从“等待者返回空”改为“回填超时结果未知”）才算新变式。
- 同一 `questionKey` + `variantId` 不重复出题；不同变式可以复用同一考点。
- 原帖与转载共用 `originGroupId`，只算一条线索；不得用转载数量制造“高频”。

## 计划构造器

`scripts/project_question_plan.py` 的 `build_question_plan` 是纯函数：只做选择约束，不联网、不调模型，候选语义由调用方给出。

```python
build_question_plan({
    "mode": "project_targeted",   # 或 "full_mock"
    "project_id": "project/12306",
    "resume_claims": [...],       # 仅已确认的 claim
    "snapshot": {...},            # 选中项目快照
    "candidates": [...],          # 候选卡
    "budget": 5,
})  # -> {"selected": [...], "rejected": [...], "warnings": [...]}
```

专项模式只接受当前 route 与项目证据一致的候选，最多选一道 `basicMechanism`，且不应用来源配比或 40% 上限。`rejected[].reason` 与 `warnings[].code` 是稳定字符串，可直接向用户解释“为什么没选”。

## 交接

用户实际答题后将 session 追加到相同路由的 `学习快照.json`；每题保留原问题、原回答、追问和时间线，原答永不被改写。没有实际回答时不创建面试 session。

专项面试结束后可依据实际回答给评价；将评价与原答分字段保存，不据单次答题宣布长期画像变化。
