---
name: child-photography-editing
description: Use when children's photographs need developer-reference style learning, background or theme edits, poster elements, local retouching, or consistent batch processing; triggers include 儿童摄影、参考样本、换背景、批量修图、人物不失真、绿色背景、儿童海报.
---

# 儿童摄影样本学习与批量创作

将开发者参考样本转化为当前批次的 Style Profile，在人物真实性绝对优先的前提下规划并执行局部编辑。此 Skill 不是选片、去重、联系表、换脸或全帧重绘工具。

## 授权与隐私前提

授权先于读取、处理或上传任何源照片。默认本地优先，永不覆盖原图。不得把儿童照片上传到第三方服务；确需上传时，必须先明确告知具体第三方目的地和用途，并取得用户明确同意。若用户只要求本地元数据检查，明确说明照片与元数据处理保持在本地。

## 固定主流程

严格执行：

```text
确认授权与本地/第三方处理边界
→ 读取开发者参考样本
→ 学习本次风格
→ 提取当前上下文中明确肯定的 Approved Treatment Hints
→ 锁定人物真实性
→ 为每张待修改图片生成 Edit Plan
→ 冻结 Batch Style Lock
→ 批量编辑
→ 单图人物 QA
→ 批次一致性 QA
→ 交付或安全回退
```

按阶段渐进读取，不要一次预加载全部参考：

- 授权与任务入口阶段：读取 `references/workflow-contract.md` 和 `references/identity-preservation.md`，先完成授权、隐私与人物锁定检查。
- 风格学习阶段：仅在编译 Style Profile 时读取 `references/style-learning.md` 和 `references/style-recipes.md`。
- 编辑规划与提示词阶段：仅在确定模式、Edit Plan 和后端提示词时读取 `references/edit-modes.md` 和 `references/prompt-templates.md`。
- 批次执行与 QA 阶段：仅在冻结批次、验收或回退时读取 `references/batch-consistency.md` 和 `references/qa-and-fallback.md`。

## 输入与输出

要求 `developerReferences`、`sourceImages`、`editIntent` 和 `outputSpec`。真正的风格迁移缺少参考样本时停止并索取样本；局部明确请求可使用用户给出的风格参数。默认输出为 `3:5`、`1200×2000`，永不覆盖原图。

支持模式：`background-only`、`skin-only`、`crop-only`、`theme-edit`、`poster-edit`、`batch-style-transfer`。

## 绝对人物锁定

禁止换脸、改变五官、脸型、头型、眼型、眼距、鼻子、嘴型、耳朵、发际线、发型、发量、身体比例、四肢比例、手脚结构、年龄感、姿势、动作和原始表情。哭泣必须保留；眼睛只能轻微提神，不能放大或改变视线；头发不能被修掉；服装默认不改。标准流程禁止全帧重生成，生成式编辑只允许作用于人物保护区域之外。

冲突优先级固定为：

```text
人物真实性 > 用户本次明确要求 > 新参考样本 > 已肯定的处理方法 > 默认风格配方
```

肤色调整仅允许约 `3%–5%` 提亮和轻微自然血色，保留婴儿真实肌理，禁止塑料皮肤。

## 风格证据隔离

新参考样本是 `Current Style Authority`，决定颜色、主题、背景、光线、元素语言、字体、纹理和构图。无法判断肯定属于风格还是处理方法时，以新样本为准。历史肯定成片只能拆成维度化的 `Approved Treatment Hints`，例如边缘干净度、肤色提亮幅度、元素密度；不得带入旧作品的颜色、主题符号、道具或字体。输出 Style Profile 时为每个维度记录 `styleEvidence`，其 `kind` 只能是 `observed`、`inferred` 或 `user-override`，并记录来源与 `[0,1]` 置信度；推断不得覆盖当前用户覆盖值。

## 执行纪律

先规划蒙版与安全区，再调用编辑后端；文字和贴纸无法避让人物时减少或取消。首张通过 QA 的结果成为批次锚点；失败结果进入 `rejected/`，不得进入 `edited/`，不得更新锚点。使用 `scripts/` 中的确定性校验器生成 Style Profile、Edit Plan、提示词和 manifest；分析脚本只读图像元数据，不改写照片。
