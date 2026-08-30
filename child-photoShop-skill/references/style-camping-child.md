# Camping Child（露营/探险主题儿童写真）

本项目第一阶段的**核心参考风格**。来自用户提供的参考图：室内棚拍 · 儿童露营主题写真。

---

## 一、风格定位

关键词：

```text
camping    explorer    earth tone    warm studio
cute       story       soft light
```

参考图的核心不是"拍了一个孩子"，而是建立了一个视觉故事：

> **"孩子正在进行小小露营探险"**

因此这个风格要处理的不是 `face retouch`，而是：

```text
child + expression + environment + props + color + theme + story
```

---

## 二、视觉优先级

```text
Child > Expression > Composition > Theme > Props
```

**绝对不能出现 `Props > Child`。**

道具服务于孩子的故事，不能压过主体。如果观者第一眼看到的是帐篷而不是孩子，这组照片就失败了。

---

## 三、色彩

### 主色

```text
khaki（卡其）      cream（奶油）     warm beige（暖米）
orange brown（橙棕）  olive green（橄榄绿）
```

### 辅助

```text
深绿      浅棕      米色
```

### 点缀

```text
黑      白
```

### 色彩特征

- 色相集中（不散）
- 饱和度中等
- 明度较高
- 整体温暖
- 无强烈冷色冲突
- 背景与服装协调

---

## 四、调色目标

```text
暖色            但不偏黄过头
肤色自然        不偏橘、不偏红
大地色统一      橙棕/卡其/橄榄绿归拢到同一色系
橙色不过饱和    这是最常见的翻车点
绿色偏柔和      不得过饱和、不得偏青
```

**橙色过饱和是露营风第一杀手**：会让整张图变成"南瓜色"，肤色被污染。

---

## 五、光线

```text
soft studio light     低反差
warm highlight        柔和阴影
```

大面积柔光，阴影较浅，脸部曝光稳定。不用硬光、不用强侧光。

---

## 六、景深

```text
主体    清晰，五官明确
背景    轻微虚化，但仍可识别主题
```

这个平衡点的意义：**保证儿童突出，同时保留故事环境。**

背景虚化过头 = 露营场景白搭了；虚化不足 = 孩子被帐篷和道具淹没。

---

## 七、必须保留的主题元素

```text
帐篷        毛绒动物      探险地图
玩具望远镜    探险帽        木质道具
卡其色服饰
```

这些是主题组成，**不得当作背景杂物删除**（见 `background-cleanup.md`）。

---

## 八、Style Profile 参考值

实际数值不要写死，由 `scripts/style_profile.py` 从用户提供的参考图实时学习。以下是该风格的大致落点，用于校验学习结果是否合理：

```yaml
name: Camping Child
temperature: warm
contrast: soft
saturation: moderate
skin: natural_warm
background: orange_beige
accent: olive_green
lighting: soft_studio
mood:
  - cute
  - warm
  - playful
  - story
constraints:
  max_strength: 0.85
```

若学习结果出现 `saturation > 0.5` 或 `temperature_hint: cool`，说明参考图判定有误或选错了参考图角色。

---

## 九、主题专项 QA

| 检查项 | 失败表现 |
|---|---|
| 橙色 | 过饱和，整图发"南瓜色" |
| 肤色 | 偏黄、偏橘，被环境色污染 |
| 绿色 | 过饱和或偏青 |
| 道具 | 抢主体，观者先看帐篷后看孩子 |
| 背景 | 杂乱，破坏探险故事感 |
| 帐篷 | 结构残缺、被 inpaint 扭曲、出现重复 |
| 毛绒玩具 | 变形、被当成杂物删除 |
| 光线 | 出现硬光或强阴影，破坏柔和感 |

---

## 十、成片装饰层（第一阶段不实现，仅记录）

参考图还包含：

```text
手写文字      漫画式装饰      简单贴纸
英文标题（如 LET'S GO CAMPING）    少量图形元素
```

这属于 `Photo Decoration Layer`，不是核心修图。第一阶段只记录规范，不强制实现。未来可作为独立模块。
