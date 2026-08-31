# 模板风格学习（Style Learning）

本 Skill 的主业务：用户给一张模板/参考图 → 学习它的光、色、背景、质感 → 稳定地应用到用户上传的儿童照片上。

核心立场：

> **学风格，不换脸。**
> Style Learning 迁移的是**全局与分区的影调、色彩、质感参数**，不包含、不推断、不迁移任何几何信息与身份信息。

借鉴自 `Zhengze-lab/photographers-eye-skill`（MIT）的 Reference Routing 思想，并叠加儿童摄影硬约束。

---

## 一、为什么 Style Profile 是纯调性参数

把 Profile 限定为"调性参数"是一个**结构性安全设计**，而不是偷懒：

| 维度 | 是否进 Profile | 理由 |
|---|---|---|
| 白平衡增益、亮度、对比、饱和度 | ✅ | 全局色彩变换，不触碰几何 |
| 色板（hex + 权重 + Lab） | ✅ | 用于背景/整体色彩收敛方向 |
| 皮肤目标色、背景目标色 | ✅ | 分区但仍是色彩变换 |
| 光位方向、光质软硬、阴影深度 | ✅ | 由亮度分布推断，用于影调复现 |
| 颗粒、微对比、高光扩散 | ✅ | 质感参数 |
| 脸型、五官比例、眼距 | ❌ | 身份信息，禁止 |
| 姿态、手势、身体比例 | ❌ | 身份/事实信息，禁止 |
| 发型、发色、服装款式 | ❌ | 个人特征，禁止 |
| 参考图中的文字、贴纸、排版 | ❌ | 不属于照片调性，且会污染成片 |

因此 `apply_style.py` 在数学上不具备改动人脸结构的能力 —— 它只做逐像素的影调/色彩映射。**身份安全由数据结构保证，而不是靠提示词约束。**

---

## 二、Profile 字段契约（schemaVersion 1.0）

```json
{
  "schemaVersion": "1.0",
  "name": "camping-child",
  "learned_at": "2026-08-30T23:40:00+08:00",
  "source": {
    "references": ["ref/camping-01.jpg"],
    "role": "color",
    "generator": "child-photoShop-skill/style_profile.py"
  },

  "exposure": {
    "mean_luma": 0.62,
    "median_luma": 0.64,
    "contrast": 0.18,
    "shadow_lift": 0.12,
    "highlight_rolloff": 0.35,
    "clip_high": 0.004,
    "clip_low": 0.003
  },

  "white_balance": {
    "r_gain": 1.05,
    "g_gain": 1.00,
    "b_gain": 0.92,
    "temperature_hint": "warm"
  },

  "color": {
    "mean_saturation": 0.31,
    "dominant_hues": [28, 34, 96],
    "palette": [
      { "hex": "#C8A87C", "weight": 0.32, "lab": [70.1, 6.2, 22.4] },
      { "hex": "#E8C4A0", "weight": 0.21, "lab": [82.3, 8.1, 18.9] }
    ]
  },

  "skin": {
    "tone_hex": "#E8C4A0",
    "target_luma": 0.74,
    "warmth": 0.18
  },

  "background": {
    "tone_hex": "#C8A87C",
    "saturation_bias": -0.05,
    "vignette": 0.10
  },

  "lighting": {
    "direction": "front-top",
    "softness": 0.78,
    "shadow_depth": 0.22
  },

  "texture": {
    "grain": 0.02,
    "microcontrast": 0.10,
    "halation": 0.05
  },

  "mood": ["warm", "soft", "story"],

  "constraints": {
    "identity_lock": true,
    "childhood_preservation": true,
    "expression_preservation": true,
    "max_strength": 0.85
  }
}
```

所有数值均为 `0-1` 归一化的**相对量**，不是设备相关的绝对参数。这样 Profile 可以跨相机、跨场次复用。

---

## 三、学习流程（learn）

```bash
python scripts/style_profile.py learn ref/template.jpg --out style_profile.json
python scripts/style_profile.py learn ref_folder/ --name camping-child --out style_profile.json
```

多张参考图时取各维度中位数，并输出维度方差；**方差 > 0.15 的维度说明参考图之间不一致，需提示用户指定主参考图**。

学习步骤：

1. 读取参考图，统一缩放至长边 1024 做统计（不改原图）。
2. 计算亮度分布 → `exposure`。
3. 计算灰世界白平衡偏差 → `white_balance`（灰世界假设失效时以中性灰区域的众数替代）。
4. 统计 HSV 饱和度与色相直方图 → `color.mean_saturation` / `dominant_hues`。
5. 用 k-means（k=6）聚类得到主色板，按像素占比排序 → `color.palette`。
6. 采样肤色区间（Lab 空间内 A/B 通道落在儿童肤色范围且亮度较高者）→ `skin`。
7. 取画面边缘环带（外围 15%）的中位色 → `background.tone_hex`。
8. 比较上/下/左/右四个亮度象限 → `lighting.direction`；高频能量 → `lighting.softness`。
9. 高频残差能量 → `texture.grain`；局部对比 → `texture.microcontrast`；亮部扩散 → `texture.halation`。
10. 写入 `constraints`，其中 `max_strength` 儿童默认 `0.85`。

---

## 四、偏差诊断（compare）

```bash
python scripts/style_profile.py compare target.jpg --profile style_profile.json
```

输出每个维度的偏差量与方向，例如：

```text
exposure.mean_luma      target=0.51  profile=0.62  delta=-0.11  → 提亮
white_balance.r_gain    target=0.98  profile=1.05  delta=-0.07  → 加暖
color.mean_saturation   target=0.28  profile=0.31  delta=-0.03  → skip
```

**决策规则**：`|delta| < 0.25` 的维度默认跳过（最小编辑原则）。只有超过阈值的维度才进入本次修图计划。

`compare` 的输出同时用于回答用户的"这张跟模板差在哪"。

---

## 五、应用（apply）

```bash
python scripts/apply_style.py input.jpg --profile style_profile.json --strength 0.8 --out edited/
```

变换链（顺序固定，全部为全局/分区的像素级映射）：

```text
1. 白平衡增益（r_gain / g_gain / b_gain）
2. 亮度映射（按 profile 的 mean_luma / contrast 做分区亮度重映射）
3. 高光滚降与暗部提亮（highlight_rolloff / shadow_lift）
4. 饱和度缩放（按 color.mean_saturation 目标值，受 strength 调制）
5. 色相收敛（把 dominant_hues 之外的色相向色板主色轻微靠拢，默认很弱）
6. 暗角（vignette）
7. 颗粒与微对比（grain / microcontrast）
```

**强度调制**：`effective = 1 + (target_ratio - 1) * strength`。`strength=0` 等于原图，`strength=1` 为完全匹配模板。

**儿童上限**：`strength` 默认 `0.8`，Profile 中 `constraints.max_strength=0.85`，超出时钳制并提示。理由是调性过度偏移会破坏儿童皮肤的真实感（过橙、过白、塑料感）。

**输出**：写入 `edited/`，原图不动，同时把本次参数追加进 `manifest.json`。

---

## 六、迭代微调映射表

用户通常只会给很短的指令。把它映射到 Profile 字段，然后**只重跑受影响的那一步**，不要整体重来。

| 用户说 | 字段 | 默认步长 | 上限 |
|---|---|---|---|
| 再暖一点 | `white_balance.r_gain` ↑ / `b_gain` ↓ | ±0.06 | 累计 ±0.20 |
| 再冷一点 | 反向 | ±0.06 | 累计 ±0.20 |
| 再亮一点 | `exposure.mean_luma` ↑ | ±0.05 | 累计 ±0.18 |
| 再暗一点 | 反向 | ±0.05 | 累计 ±0.18 |
| 对比再柔一点 | `exposure.contrast` ↓ | ±0.05 | 累计 ±0.15 |
| 对比再强一点 | 反向 | ±0.05 | 累计 ±0.15 |
| 颜色再淡一点 | `color.mean_saturation` ↓ | ±0.08 | 累计 ±0.25 |
| 颜色再浓一点 | 反向 | ±0.08 | 累计 ±0.25 |
| 皮肤再透一点 | `skin.target_luma` ↑ | ±0.04 | 累计 ±0.12 |
| 背景再虚/再干净点 | 走背景清理流程，不是调色 | — | — |
| 再像模板一点 | `strength` ↑ | +0.10 | 0.85 |
| 不要太像模板 | `strength` ↓ | -0.10 | 0.20 |
| 不要动脸 | `constraints.identity_lock=true`，禁用一切局部重绘 | 强制 | — |

**迭代纪律**：

1. 单轮只调用户点到的维度，不得顺手改别的。
2. 每轮后重跑 QA（至少 Skin QA + Artifact QA）。
3. 每轮参数写入 manifest，保留可追溯链。
4. 累计调整触达上限时停止，并告知用户"继续会偏离儿童皮肤真实感"，改用其他手段（如背景清理）解决问题。

---

## 七、失败与回退

| 情况 | 处理 |
|---|---|
| 参考图与用户照片拍摄条件差异极大（如参考图是外景、用户图是棚拍） | 提示仅迁移色彩与饱和度，跳过 `lighting`；或建议换参考图 |
| 套用后皮肤过橙/过黄 | 降低 `strength`，并对皮肤分区单独降低饱和度偏移 |
| 套用后背景色彩与主题冲突（如露营风套到生日照导致蛋糕变色） | 把 `background.tone_hex` 的迁移强度单独降到 0.3 |
| 用户要求"连脸也修成参考图那样" | **拒绝**。说明这属于身份替换，超出儿童写真精修范围 |
| `apply` 后 QA 不通过 | 按 SKILL.md §十四 依次降级：降强度 → 缩范围 → 换后端 → 回退原图 |

---

## 八、与主题的配合

Style Profile 解决"调性"，主题（Camping / Forest / Birthday / Home Story / Parent Child）解决"内容优先级"。

顺序：**先定主题 → 再学调性 → 最后套用**。主题决定哪些道具必须保留、哪些颜色不能偏（如生日照的蛋糕颜色、森系的绿色不能过饱和），这些约束写在 `references/style-camping-child.md` 等主题文件中，作为 Profile 应用时的边界条件。
