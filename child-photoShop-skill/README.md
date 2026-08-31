# child-photoShop-skill · 儿童摄影馆后期 Agent

面向儿童摄影馆、儿童摄影师与后期修图师的后期 Skill。

核心业务是**从一张模板/参考图学习视觉风格，再把这套风格稳定地套到用户上传的儿童照片上**，然后按用户的简单指令迭代（"再暖一点""再亮一点""不要动脸"），全程锁死儿童的身份、年龄与表情。

一句话总纲：

> **Do not redesign the child. Retouch the photograph.**
> 不重新设计孩子，只精修照片。

---

## 快速开始

```bash
# 1) 从模板图学习风格画像
python scripts/style_profile.py learn 模板图.jpg --out style_profile.json

# 2) 看看待修图和模板差在哪
python scripts/style_profile.py compare 客片.jpg --profile style_profile.json

# 3) 套用（strength 默认 0.8，儿童照片上限 0.85）
python scripts/apply_style.py 客片.jpg --profile style_profile.json --strength 0.8 --out edited/

# 4) 批量：建 manifest → 逐张处理 → 一致性 QA
python scripts/batch_manifest.py init ./originals --session camping --out manifest.json
python scripts/duplicate_detection.py ./originals          # 连拍去重
python scripts/image_quality.py ./originals                # 技术质量打分
python scripts/contact_sheet.py ./selected --out reports/contact_sheet.jpg
```

依赖只有 `pillow` 与 `numpy`；`opencv-python` 缺失时脚本自动降级。

---

## 目录结构

```text
child-photoShop-skill/
├── SKILL.md                             主入口（先读这个）
├── agents/openai.yaml                   界面元信息
├── README.md                            本文件
├── references/                          按需加载的规范文档
│   ├── style-learning.md                ★ 模板风格学习的完整流程与 Profile 字段契约
│   ├── identity-preservation.md         身份保持（改脸之前必读）
│   ├── childhood-preservation.md        童真保持、防成人化
│   ├── expression-preservation.md       表情质量 ≠ 笑容分数
│   ├── portrait-retouch-guidelines.md   分区修图：皮肤/眼/牙/头发/衣服
│   ├── photo-culling-guidelines.md      儿童专用选片打分
│   ├── background-cleanup.md            背景清理与道具保护
│   ├── color-grading.md                 调色与各风格色板
│   ├── style-camping-child.md           露营主题写真
│   ├── qa-guidelines.md                 6 类 QA 与交付清单
│   ├── child-photography-principles.md  儿童摄影审美优先级
│   └── open-source-research.md          开源调研与许可证边界
├── scripts/                             确定性工具（只做 Agent 不擅长的事）
│   ├── style_profile.py                 learn / compare
│   ├── apply_style.py                   套用风格画像（身份安全）
│   ├── build_generation_prompt.py       风格画像 → 生图提示词（禁令全集）
│   ├── analyze_image.py                 尺寸/EXIF/ICC/直方图
│   ├── image_quality.py                 锐度/曝光/过曝评分
│   ├── duplicate_detection.py           感知哈希 + 时间邻近去重
│   ├── batch_manifest.py                manifest 生成与更新
│   └── contact_sheet.py                 选片联系表
├── style-library/                       风格库与加权混合（静态前端原型）
│   ├── index.html                       页面骨架
│   ├── styles.css                       样式
│   ├── profile-library.js               纯逻辑层：混合、校验、导出
│   ├── app.js                           界面层：卡片、滑块、结果
│   └── smoke-test.js                    零依赖冒烟测试：node smoke-test.js
└── tests/                               133 条测试（含契约测试与行为测试）
```

---

## 为什么它是身份安全的

很多"AI 修图"会顺手把孩子的脸改一改：瘦一点、白一点、眼睛大一点。这在成人写真里也许可以接受，在儿童写真里是事故——父母一眼就能看出来，而且那不再是他们的孩子。

本 Skill 不靠提示词约束这件事，而是**让它在结构上不可能发生**：

1. **Style Profile 里没有几何字段。** 画像只有全局/分区的影调、色彩、质感参数——没有脸型、五官、姿态、发型、服装身份。`tests/` 里有一条测试递归扫描整个 Profile，任何身份类字段出现即失败。你想调也调不出来，因为根本没有那个旋钮。
2. **应用阶段是逐像素的色彩映射。** 没有卷积、没有 inpainting、没有生成式重绘。测试用「相同输入像素必须映射到相同输出像素」这条不变量来守住它——注入一个高斯模糊就会立刻失败。
3. **面部结构修改在任何强度等级恒为 0%。** L1/L2/L3 都是 0%，而不是成人 Skill 里常见的 5%。

---

## 与其他项目的差别

| 常见做法 | 本 Skill |
|---|---|
| 参考图＝照抄 | 参考图先指派**唯一角色**（Color / Lighting / Texture / Composition / Degree / Target / Negative），各自有明确的迁移与禁止清单 |
| 笑容分数越高越好 | 评 `expression quality`，不是 `smile score` |
| 没看镜头 → 低分 | `looking_at_camera` 只是**弱**评分项 |
| 换牙期牙齿要修整齐 | 换牙期是受保护的**年龄特征** |
| 背景杂物＝全删 | 先做**道具保护**判定，帐篷、气球、蛋糕属于主题组成 |
| 美白磨皮 | 不美白；磨皮 ≤15% |
| 修不好就重生成 | 全图重生成不属于标准精修；失败按降级阶梯回退，终点是保留原图 |

---

## 开源调研与许可证

开发前调研了 6 个同类开源项目与 4 个后端方案，逐个记录了「借鉴了什么／拒绝了什么／风险」：见 `references/open-source-research.md`。

- **未复制任何一行外部代码。**
- 借鉴的设计来自 MIT 许可的两个项目：`Zhengze-lab/photographers-eye-skill`（参考图角色路由）、`lovstudio/professional-portrait-skill`（质量门禁表）。
- 明确**拒绝**了同类项目中常见的"皮肤美白""面部调整"等行为——它们与儿童身份/年龄/童真原则冲突，本 Skill 以 §99 为最高优先级，儿童原则优先于任何开源项目的行为。
- 无 GPL / AGPL 污染。生成式后端（InstantID / PuLID / DZ-FaceDetailer 等）仅登记未集成，留给第二阶段。

---

## 已知限制

- **脚本只做调色与度量，不做重绘。** 去红点、去灯架、修衣服需要图像编辑后端。执行环境没有后端时必须明说限制并给出可执行步骤，**不得谎称已修图**。
- 生成式精修后端尚未集成（第一阶段刻意延后，先把身份安全的地基打牢）。
- 人脸检测相关的打分（身份漂移余弦相似度 ≥0.90）需要接入人脸模型后才能自动化，目前是人工 QA 项。
- 阈值是在合成 fixture 上标定的；真实照片细节丰富得多，首批真实样本跑完后需要重新校准 `image_quality.py` 的两个常数。
- **风格库页面是前端原型。** `style-library/` 用的是内置静态风格数据，保存接口为占位实现（只校验、不落盘），只有「导出 JSON」是真的。真实风格画像应由 `scripts/style_profile.py learn` 从模板图学出后再接进来。

---

## 测试

```bash
cd child-photoShop-skill
python -m unittest discover -s tests -p "test_*.py"
```

133 条，全绿。分五层：

- **契约测试**（`test_skill_contract.py`）：SKILL.md 是否仍然写明了每一条硬规则，references/scripts 链接是否悬空；README 目录树与磁盘、与 SKILL.md 脚本表是否三方一致。文档会静默腐烂，这是绊线。
- **提示词测试**（`test_generation_prompt.py`）：编译出的生图提示词是否始终携带完整禁令全集，是否不随 Profile 缩水；三种模式的强度上限与隐私声明是否正确。
- **行为测试**（`test_style_learning.py`）：核心业务的量化验收——套用风格后亮度/饱和度/色温是否朝模板收敛，高光溢出是否低于 1%，逐像素不变量是否成立。
- **工具测试**（`test_scripts.py`）：打分能否区分清晰与模糊，连拍能否正确聚成一簇，manifest 能否往返落盘。
- **迭代测试**（`test_style_learning.py::IterationTests`）：连跑四轮会收敛到定点而不是每轮多偏一点；已达标的分量会被跳过。

测试全部使用合成 fixture，仓库里不会存放任何真实儿童照片。

风格画像库另有一层零依赖的 JS 冒烟测试：

```bash
cd child-photoShop-skill/style-library
node smoke-test.js    # 22 项，零依赖
```

覆盖权重归一化、加权混合、颜色混色、身份字段校验与导出。界面出问题肉眼看得见，混合系数算错了看不见 —— 这一层是管后者的。前端的 `NUMERIC_DIMS` 与 `BANNED_KEYS` 从 Python 侧逐字复制而来，身份安全边界在浏览器里同样成立。
