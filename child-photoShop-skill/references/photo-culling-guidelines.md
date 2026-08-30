# 自动选片规范（Photo Culling Guidelines）

儿童摄影一个场次动辄几百张，其中大量是连拍废片。选片的价值不在于"挑出技术上最好的"，而在于**挑出情绪最好、故事最完整、重复最少的一组**。

---

## 一、评分维度与权重

总分 100。

### 基础技术维度（40 分）

| 维度 | 分值 | 说明 |
|---|---|---|
| `sharpness` | 12 | 拉普拉斯方差等锐度指标 |
| `focus` | 8 | 主体是否在对焦平面上 |
| `exposure` | 8 | 过曝/欠曝、高光剪切、暗部死黑 |
| `motion_blur` | 7 | 运动模糊惩罚 |
| `composition` | 5 | 主体位置、边缘安全、裁剪可用性 |

### 儿童专用维度（60 分）

| 维度 | 分值 | 说明 |
|---|---|---|
| `expression` | 18 | **表情质量**，不是笑容分数 |
| `child_emotion` | 12 | 情绪强度与真实性 |
| `story_value` | 10 | 故事性与情境完整度 |
| `natural_expression` | 8 | 是否自然自发，而非摆拍僵硬 |
| `interaction_quality` | 7 | 与道具/人物/环境的互动质量 |
| `theme_quality` | 5 | 主题呈现是否清晰 |

**权重说明**：通用选片实现（如 `photo-cull-retouch`）通常把技术质量放在 35/100、人像质量 25/100。本 Skill 把**儿童情绪相关维度提到 60/100**，因为家长选片的决定因素几乎从来不是锐度，而是"这张像不像我的孩子、有没有那个瞬间"。

### 惩罚项

```text
blur_penalty          模糊，含失焦与运动模糊
obstruction_penalty   主体被遮挡（手挡脸、道具挡脸、他人遮挡）
duplicate_penalty     与同组已选图重复
```

---

## 二、儿童专用硬规则

### 规则 1：不强制看镜头

`looking_at_camera` 只是弱评分项（≤ 3 分的浮动）。

```text
❌ not looking at camera = bad
✅ looking at camera = 弱加分项
```

孩子看玩具、看父母、看地面、大笑、专注玩耍同样可能是优秀照片。**互动方向往往比镜头更有价值。**

### 规则 2：表情质量 ≠ 笑容分数

评的是 `expression quality`。笑、好奇、开心、专注、惊讶、委屈、发呆都可能是优秀表情。

判定维度：真实性、强度、眼部参与、与情境一致、感染力。详见 `expression-preservation.md`。

### 规则 3：连拍只留最佳帧

10 张几乎相同的笑脸只保留 **1-2 张**最佳帧。

---

## 三、连拍去重

输入：整个目录。
方法（见 `scripts/duplicate_detection.py`）：

```text
perceptual similarity（pHash + dHash 汉明距离）
+ time adjacency（EXIF 拍摄时间或文件序号邻近）
```

步骤：

1. 计算每张图的感知哈希。
2. 按时间/序号排序，在滑动窗口内比较汉明距离。
3. 距离低于阈值（默认 dHash ≤ 10）的归入同一 cluster。
4. 每个 cluster 内保留 `expression + sharpness` 综合分最高的 1-2 张。
5. 其余标记 `duplicate_penalty` 并落入 `rejected/`。

**时间邻近很重要**：儿童连拍中会出现姿势相似但表情不同的照片，仅靠哈希容易误杀。时间窗口内才做聚类，跨场次不聚类。

---

## 四、淘汰规则（硬否决）

出现以下情况直接淘汰，不看总分：

- 主体严重模糊且无法修复
- 主体被完全遮挡
- 曝光严重失误（大面积死白或死黑）
- 孩子明显不适（哭闹到表情痛苦、摔倒瞬间）
- 出现穿帮且无法修复（摄影师入镜、器材大面积入镜）

**注意**：哭闹不等于淘汰。儿童真实的哭、闹、委屈表情有极高故事价值，只有"孩子明显处于痛苦/危险"才淘汰。

---

## 五、选取与多样性

1. 按总分降序排列。
2. 默认保留前 **20%**，最少 1 张、最多 30 张（可用 `--keep-count` / `--keep-ratio` / `--min-score` 覆盖）。
3. **多样性修正**：确保入选集合中
   - 表情不单一（不要 30 张全是一个笑容）
   - 景别有变化（全身、半身、特写）
   - 故事完整（主题道具、互动、环境各有覆盖）
4. 多样性修正优先于纯分数排序：宁可要第 25 名的新表情，也不要第 3 名的第 5 个重复笑容。

---

## 六、输出

```text
output/
├── selected/                    入选原图副本
├── rejected/                    落选
├── edited/                      精修成品
├── reports/selection_report.csv
├── reports/contact_sheet.jpg
└── manifest.json
```

`selection_report.csv` 字段：

```text
filename, sharpness_score, focus_score, expression_score,
composition_score, exposure_score, story_score,
duplicate_group, overall_score, selected, reason
```

`reason` 必须写人类可读的中文理由，例如"表情生动但连拍重复，已被同组更清晰帧替代"。家长和摄影师要看这个字段做复核。

---

## 七、人在回路

AI 选片是**初筛**，不是终审。

- 输出 `contact_sheet.jpg` 供摄影师快速复核。
- `rejected/` 保留全部落选图，不做删除。
- 明确告知用户：这是 AI 初筛结果，建议人工复核后再交付客户。
