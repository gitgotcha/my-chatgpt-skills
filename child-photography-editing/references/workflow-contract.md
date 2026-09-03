# 工作流契约

## 唯一主链

读取开发者样本 → 编译 `StyleProfile` → 收集维度化 `ApprovedTreatmentHints` → 为每张图建立 `EditPlan` → 冻结 `BatchStyleLock` → 批量编辑 → 单图人物 QA → 批次一致性 QA → 交付或回退。

## 输入

- `developerReferences`: 至少一张开发者参考样本或已确认的 Style Profile。
- `sourceImages`: 一张或多张待修改图片。
- `editIntent`: 六个受支持的模式之一。
- `outputSpec`: 默认 `3:5`、`1200×2000`，用户明确值优先。
- `textSpec`: 可选文字、语言、字体气质和避让区域。
- `perImageOverrides`: 可选构图例外，不得覆盖人物硬约束。

缺少待修改图片时不得假装已经处理。真正的风格迁移缺少样本时停止并索取样本。

## 输出

不得覆盖原图，交付目录包含 `edited/`、`originals/`、`reports/style-profile.json`、`reports/batch-manifest.json`、`reports/qa-report.json` 和失败结果 `rejected/`。
