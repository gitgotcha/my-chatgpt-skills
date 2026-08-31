# Open Source Research

调研日期：2026-08-30
调研方式：GitHub Search API + 浅克隆阅读源码
调研目的：为 `child-photoShop-skill` 找到可复用的架构思想，避免重复造轮子。

调研结论一句话：**已有项目在"通用人像精修"和"选片打分"上提供了可直接借鉴的骨架，但没有任何一个项目处理儿童摄影的身份/童真/表情保持问题。儿童摄影特有的约束必须自建。**

---

## 一、Skill 形态的同行（最相关）

### 1. dudachun/photo-cull-retouch

| 项 | 内容 |
|---|---|
| URL | https://github.com/dudachun/photo-cull-retouch |
| License | **无许可证**（默认版权，不可复制代码，仅可参考思想） |
| Stars | 18 |
| 结构 | `SKILL.md` + `scripts/photo_cull_retouch.py` + `run.sh` + `install.sh` |

**Useful Ideas（已借鉴）**

- **输出契约固定**：`edited/` + `selected_originals/` + `score_report.csv` + `manifest.json` + `contact_sheet.jpg`。本项目沿用，并加上 `originals/` 保护层和 `reports/`。
- **100 分制打分 rubric**：技术质量 35 / 人像质量 25 / 构图 20 / 色彩情绪 15 / 可修潜力 5。本项目在其基础上重排权重（见下文差异）。
- **可移植性原则**："所有命令相对 SKILL.md 所在目录解析，不使用机器绝对路径"。本项目采纳。
- selection 默认保留前 20%，min 1 / max 30，可用 `--keep-count` / `--keep-ratio` / `--min-score` 覆盖。

**What We Did Not Reuse**

- 其"Retouching Standard"包含 `Skin whitening`（皮肤美白）与 `Face adjustment`（面部调整），这两项与本项目儿童原则直接冲突，不采纳。
- 其默认值面向成人/旅拍，不含连拍去重与情绪评分。

**Risk**

- 无许可证 → 只能借鉴思想，禁止复制任何代码。本项目代码全部自写。

---

### 2. qzfcoder/photo-retouch-pro

| 项 | 内容 |
|---|---|
| URL | https://github.com/qzfcoder/photo-retouch-pro |
| License | **无许可证** |
| Stars | 3 |
| 结构 | `SKILL.md` + `references/{aesthetic-direction,output-template,prompt-standard,retouch-judge-rules}.md` + `examples/` |

**Useful Ideas（已借鉴）**

- **量化阈值写进规范**：磨皮默认 15-25%、上限 35%；脸型/身形调整默认 0%、明确要求时上限 5%；全局饱和度 ±20% 以内。本项目采用了"把抽象审美写成可验证数字"的做法，但儿童项目的阈值更严（磨皮 ≤15%，脸型调整恒为 0%）。
- **两遍修图法**：Pass A 技术校正与清理，Pass B 主体特征强化。本项目沿用为"技术层 → 表达层"。
- **Protected Regions 前置**：编辑前先锁定受保护区。本项目升级为 Identity Lock。
- **验收门（Acceptance Gate）**：不通过就重修，而不是交付弱结果。本项目采纳为 QA Engine。

**What We Did Not Reuse**

- 其 `impact-plus` 强度档要求"主体比背景亮 0.35-0.65EV、背景竞争降低 15-30%"，这是成人商业片的强对抗逻辑，儿童写真不需要这么强的主体压制。本项目不设 impact-plus 等价档。
- 其人像逻辑默认"美白 + 活力提升"，不适用于儿童。

**Risk**

- 无许可证，仅借鉴思想。

---

### 3. Zhengze-lab/photographers-eye-skill

| 项 | 内容 |
|---|---|
| URL | https://github.com/Zhengze-lab/photographers-eye-skill |
| License | **MIT**（友好） |
| Stars | 1 |
| 结构 | `photographers-eye/SKILL.md` + `references/{genre-recipes,master-methods,prompt-templates,quick-fix-maps,style-directions,usage-examples}.md` |

**Useful Ideas（已借鉴，本项目最核心借鉴项）**

- **Reference Routing（参考图角色路由）**——直接解决本项目 §28.6 的"参考图模板学习"需求：

  | 角色 | 含义 | 迁移什么 |
  |---|---|---|
  | `Degree reference` | 只匹配修图强度 | 强度，不抄色板/构图 |
  | `Color reference` | 借色彩关系与对比逻辑 | 色相/饱和度/对比 |
  | `Composition reference` | 借裁切比例、主体尺度、留白 | 构图 |
  | `Lighting reference` | 借主光/补光/轮廓光方向、软硬、色温、阴影密度 | 光位与光质 |
  | `Texture reference` | 借颗粒、锐度、皮肤质感 | 质感 |
  | `Target reference` | 用户明确说"修成这样" | 全风格，但不许抄脸 |
  | `Negative reference` | "不要这样" | 反向排除 |

  本项目将其改造为 `Style Reference Workflow` 的核心决策表，并**强制叠加儿童禁令：任何角色下都不得迁移 face / identity / body / pose / hair / 服装身份**。

- **Style menu mode vs Direct prompt mode**：请求模糊时先给 4-6 个风格路线让用户选，请求明确时直接出方案。本项目采纳为"模糊请求先给风格菜单"。
- **Delivery type 分层**：original fidelity repair / commercial rescue / photographic creative reconstruction / generative reconstruction。本项目映射为 Level 0-3 修图强度 + Creative Edit Mode。

**Risk**

- MIT，思想可自由借鉴。本项目未复制任何代码。

---

### 4. lovstudio/professional-portrait-skill

| 项 | 内容 |
|---|---|
| URL | https://github.com/lovstudio/professional-portrait-skill |
| License | **MIT** |
| Stars | 0 |

**Useful Ideas（已借鉴）**

- **Quality Gate 表格化**：`| Area | Pass condition | Common failure |` 三列表。本项目 `qa-guidelines.md` 采用同一形式，并扩展到儿童专项（成人化、童真丢失、表情被修正）。
- **Decision rule**：身份失败必须重修；风格漂移时回到原图缩小编辑范围，而不是再叠一遍全图 pass。本项目采纳为 Retry Strategy 第四步。
- `cases/cases.json` 作为用例索引 + CI 校验的写法值得参考，本项目的 `tests/` 采用等价的用例驱动测试。

**Risk**

- 面向职业形象照（成人商务），其"发型重建""去帽"等能力对儿童无意义，不引入。

---

### 5. camharris/photo-culling-agent

| 项 | 内容 |
|---|---|
| URL | https://github.com/camharris/photo-culling-agent |
| License | **无许可证** |
| Stars | 0 |

**Useful Ideas**

- 分级为 `keep` / `toss` 两档，并保留 human-in-the-loop 复核（Gradio）。本项目保留"AI 选片 + 人工复核"的定位，但去掉 UI 依赖。
- 模块化拆分：`ImageProcessor` / `GPTAnalyzer` / `MetadataManager`。本项目把对应职责压缩到 `scripts/` 的四个确定性脚本。

**What We Did Not Reuse**

- 依赖 GPT-4o + LangGraph + Gradio，过重，且是风景照场景（无表情/身份维度）。YAGNI，不引入。

**Risk**

- 无许可证；且强依赖云 API，与本项目 local-first 隐私原则冲突。

---

### 6. WWIIITT/PortraitRetouch

| 项 | 内容 |
|---|---|
| URL | https://github.com/WWIIITT/PortraitRetouch |
| License | **无许可证** |
| Stars | 0 |

**Useful Ideas**

- 交互式会话记忆（interaction memory）：把用户每轮反馈记住，用于下一轮迭代。本项目采纳为"用户简单指令驱动的迭代"上下文，但以 `manifest.json` 落盘而非内存态。
- `src/agents/retouch_planner.py` 体现"分析 → 规划 → 执行"分离，与本项目 Retouch Decision Engine 一致。
- 分区处理：`face_local_retouch` / `cloth_local_retouch` / `body_skin_adjust`。本项目沿用分区思路（脸/衣服/背景/道具分区决策）。

**Risk**

- 无许可证；依赖 Gemini API（云端），与儿童照片隐私原则冲突，仅借鉴架构。

---

## 二、图像后端（能力层，第二阶段再接）

| 项目 | License | 用途 | 是否第一阶段引入 |
|---|---|---|---|
| instantX-research/InstantID | Apache-2.0 | 身份保持的人像生成 | 否，仅记录 |
| ToTheBeginning/PuLID | Apache-2.0 | 身份保持，扰动更小 | 否，仅记录 |
| cubiq/ComfyUI_InstantID | Apache-2.0 | ComfyUI 封装 | 否 |
| balazik/ComfyUI-PuLID-Flux | Apache-2.0 | FLUX 下的 PuLID | 否 |
| nicofdga/DZ-FaceDetailer | MIT | 面部重绘/修复 | 否，仅记录 |
| modelscope/facechain | Apache-2.0 | 人像生成流水线 | 否，偏生成而非精修 |

**结论：第一阶段不安装、不集成任何图像生成后端。** 本 Skill 第一阶段交付的是"理解 + 规划 + 约束 + 路由 + QA"能力，图像后端由执行环境按需选择。这与规范 §32（Skill 层不承担全部图像计算）一致。

**与本项目原则的冲突点（记录备查）**：InstantID / PuLID / FaceChain 的设计目标是"生成特定身份的人像"，其典型用法是重新生成人脸。用于儿童写真精修时必须把 denoise / identity weight 压到极低，且必须通过 Identity QA，否则直接回退。规范 §99 规定：开源实现与本项目儿童原则冲突时，以儿童原则为最高优先级。

---

## 三、许可证核对汇总

| 项目 | License | 可复用代码 | 可借鉴思想 |
|---|---|---|---|
| dudachun/photo-cull-retouch | 无 | ❌ | ✅ |
| qzfcoder/photo-retouch-pro | 无 | ❌ | ✅ |
| camharris/photo-culling-agent | 无 | ❌ | ✅ |
| WWIIITT/PortraitRetouch | 无 | ❌ | ✅ |
| Zhengze-lab/photographers-eye-skill | MIT | ✅ | ✅ |
| lovstudio/professional-portrait-skill | MIT | ✅ | ✅ |
| InstantID / PuLID / ComfyUI_InstantID / ComfyUI-PuLID-Flux | Apache-2.0 | ✅ | ✅ |
| DZ-FaceDetailer | MIT | ✅ | ✅ |
| modelscope/facechain | Apache-2.0 | ✅ | ✅ |

**执行结果：本项目未复制任何一行外部代码。** 所有脚本从零编写，仅复用上表中标注 ✅ 的架构思想。无 GPL/AGPL 传染性风险。

---

## 四、与既有实现的差异化（本项目新增，同行都没有）

1. **儿童身份/童真/表情三重保持**（Identity / Childhood / Expression Preservation）——所有同行项目都是通用人像，无此约束。
2. **临时性瑕疵 vs 永久性特征区分**——痣、胎记、雀斑默认保留，同行的"blemish cleanup"不做区分。
3. **儿童选片专用指标**——`child_emotion` / `child_engagement` / `natural_expression` / `cute_moment` / `story_value`，且"看不看镜头"只作弱评分项（同行的 portrait quality 普遍把"眼睛/看镜头"作为强信号）。
4. **连拍去重**——perceptual similarity + time adjacency，同行的 culling 无去重。
5. **道具保护（Prop Protection）**——帐篷/毛绒玩具/蛋糕不能被当背景杂物删除，同行无此概念。
6. **儿童照片隐私 local-first 硬约束**——同行多个项目默认调云 API，本项目默认禁止未经声明上传。
7. **主题风格 Profile（Camping / Forest / Birthday / Home Story / Parent Child）**——同行的 style 是成人向的胶片感/电影感/日杂，无儿童主题体系。
