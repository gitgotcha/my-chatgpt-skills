# 画像与存储契约

所有持久化只通过 `submit_event` 提交，由 Worker 校验并物化。技能不直接访问存储层，也不得在写入失败时回退到旧目录。

## 规范目录

唯一规范根是 `DriveRoot/my-chatGPT-skills/`。本领域的目录形状为：

```text
DriveRoot/my-chatGPT-skills/
├── user-registry/
│   └── registration-<userId>.json
└── users/<userId>/
    └── resume-knowledge/
        ├── sources/resume/snapshots/resume-<version>-<fingerprint>.json
        ├── question-bank/snapshots/question-bank-<version>-<eventId>.json
        ├── events/event-<eventId>.json
        ├── profile/snapshots/snapshot-<UTC>-<headEventId>.json
        └── plans/daily/daily-plan-<localDate>-<planId>.json
```

`users/<userId>/resume-knowledge/` 是本领域的唯一写入范围。全局注册位于 `user-registry/`，用户目录位于 `users/<userId>/`。

## 事件类型

| 事件 | 物化结果 |
| --- | --- |
| `resume-knowledge.resume-ingested` | 简历声明快照与文件指纹 |
| `resume-knowledge.claim-confirmed` | 记录确认，供下一版题库使用 |
| `resume-knowledge.claim-rejected` | 记录否认，供下一版题库使用 |
| `resume-knowledge.question-bank-created` | 与简历版本绑定的题库快照 |
| `resume-knowledge.daily-plan-created` | 不可变的当日题单 |
| `resume-knowledge.answer-scored` | 首次有效评分事件与新的掌握度快照 |

## 掌握度

题目掌握度采用 EWMA：

```text
首次：masteryScore = 本次得分
后续不同日期：newMasteryScore = 0.6 * 本次得分 + 0.4 * 原掌握度
```

知识点掌握度是该知识点下所有已考规范题当前掌握度的平均值。未考题保持 `untested`，不按 0 分计入平均值；同时单独保存覆盖率，避免少量高分掩盖大量未考题。

## 每日一次计分

计分幂等键为 `userId + localDate + questionKey`。同一用户、同一自然日、同一 questionKey，只接受当天第一次回答计分。

- 当天第一次回答：生成反馈，提交 `answer-scored`，更新掌握度并生成快照。
- 当天再次回答：仍生成完整反馈，但明确提示今日已计分；不提交事件，不更新画像。
- 次日同题再次出现：生成新的日期级幂等键，允许重新计分。

## 每日题单

每日默认五题：两道当前题目掌握度最低的题、一道尚未考察的简历明示题、一道项目场景追问题、一道历史低分复测题。

选择必须去重，同一 `questionKey` 不在同一题单中重复出现。弱项排序依次考虑：低题目掌握度 -> 低知识点掌握度 -> 更久未复测 -> 更高简历相关度。未考题使用专门的新题位置，不按 0 分混入低分排序。

证据不足以安全提供五个不同题目时，返回更少题目并解释原因，禁止使用无依据的通用八股补齐。

当日题单已创建后不可变，已存在时原样返回，不重新生成。当天上传的新简历从下一个尚未创建题单的日期生效。

## 快照

每个首次有效 `answer-scored` 事件后，Worker 运行 reducer 生成新的不可变快照，包含简历版本、`headEventId`、知识点掌握度、题目掌握度、题库覆盖率、近期错误与回答问题、按优先级排序的薄弱点、下一轮推荐复习内容与 `sourceEventKeys`。

快照是事件的派生结果，技能不上传也不覆盖快照。
