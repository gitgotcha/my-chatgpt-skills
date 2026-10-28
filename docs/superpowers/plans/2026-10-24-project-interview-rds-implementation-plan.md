# 项目学习 × 模拟面试 × RDS 项目快照 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 用户手动提交；执行者不 commit、不 push、不部署、不安装插件缓存。

**Goal:** 保留已认可的项目讲解输出，让正式项目问答与模拟面试共享**按项目隔离**的服务端证据，并完全排除次日开场回顾。

**Architecture:** 复用既有 `interview.session.completed` / `interview.review.completed` 事件链，新增 `projectContractVersion:1` 扩展、两张身份映射表、服务端项目派生行与有界构建 v2；技能侧新增纯构造函数，教学提纲沿用 generic profile 的 `learning-outline` 观察。新能力由 `capabilities.features.interviewProjectSnapshots` 控制，旧事件与旧查询零改动。

**Tech Stack:** Node.js ≥22 / ES modules、Cloudflare Worker / D1 / Queue、SQLite Outbox、Python 3 `unittest`、JSON Schema 2020-12、Markdown/PNG。

**Spec:** [项目学习 × 模拟面试 × RDS 项目快照：联合设计规格](../specs/2026-10-24-project-interview-rds-design.md)

**Repositories**

| 代号 | 根目录 | 本次基线 | 执行前必须重查 |
|---|---|---|---|
| S（技能） | `C:\Users\27846\my-chatgpt-skills` | `7c588e4fd2e0e35ccc5a6f2fa8e527806af0deae` | HEAD、`git status --short` |
| R（运行时） | `C:\Users\27846\my-chatgpt-mcp-v2` | `4f810094b65d0e9c6fc2d719aa97ddb2becaa7c2` | HEAD、`git status --short` |
| E（教学证据，只读） | `D:\Project\train-12306` | `c7d862d85cd4121655f32304a8abaac3a6da030c`（工作树有既有改动） | 只读，不修复、不提交 |

**启动语（可直接粘贴给 Codex）**

> 读取 `docs/superpowers/specs/2026-10-24-project-interview-rds-design.md` 与 `docs/superpowers/plans/2026-10-24-project-interview-rds-implementation-plan.md`。从 T0 开始逐任务执行：每个任务先写失败测试并运行（RED），再实现，再用同一命令验证（GREEN），保留原始输出与退出码。不要 commit、push、部署或安装插件；不要覆盖既有未提交改动。全部完成后按“交回物”生成实施报告与 44 项验收表。

## Global Constraints

- 路径书写：S 与 R 是**两个仓库**，下文所有相对路径分别相对其根目录展开；跨仓库改动必须在同一份实施报告里列出。
- 不覆盖既有未提交改动。S 当前有 `tests/test_rds_v2_skill_contract.py`、`tests/test_repository_storage_contract.py` 的修改（各 +1 行，加入 `adaptive-study-planning`）与 5 个未跟踪路径；R 当前有 3 个未跟踪计划文档。不得 stash/reset/清理。
- 冻结代码不动：S 内 `services/reliable-drive-sync-worker`、`tools/reliable-drive-sync-mcp`、`cloud-mcp`，以及安装缓存 `C:\Users\27846\.codex\plugins\cache\personal\my-chatgpt-skills\…`。
- 云读写唯一入口 `submit_event`；外层业务 envelope 保持 `schemaVersion:"1.2"`；generic 内部 `schemaVersion:"1.0"`；项目学习 domain 为 `backend-project-learning`。
- 原始作答不可改：新尝试新 `attemptId`，修订评价新 `reviewVersion`，重试时 requestId/eventId/eventKey 与内容不变。
- 回顾零业务写入：不能通过 outline、附件、报告或 `profileChanges` 旁路。
- 未知不得当零：`projection_not_found` / `building=true` / 读取失败都是“未知”。
- 容量超限在接纳前拒绝，不截断：48 KiB envelope / 24 KiB 单题 / 8 KiB 评价。
- 既有测试失败照实记录，不删除用例来迁就新字段；修复既有失败时必须在报告中单独列出。
- 每个任务先写失败测试（RED），再实现，再跑同一命令（GREEN），并保留原始输出。
- 不自动 commit/push/部署/安装；不写个人 RDS；合成数据只进隔离本地测试库。

**Windows 执行约定**

```powershell
$env:PYTHONUTF8 = '1'   # 否则中文文档读取可能出现乱码断言
```

Python 套件按技能目录运行，`reviewing-java-backend-interviews` 必须 `cd` 进目录（其测试 `import scripts.*`）：

```powershell
cd C:\Users\27846\my-chatgpt-skills\reviewing-java-backend-interviews
python -m unittest discover -s tests -v
```

## 执行顺序

```text
T0 → T1 → T2 → T3 → T4 →┐
T0 → T1 → T5 ───────────┼→ T7
T0 → T1 → T6 ───────────┘
```

T2 依赖 T1 的合同；T3 依赖 T2 的身份表与接纳顺序；T4 依赖 T3 的派生行。T5、T6 只依赖 T1，可与 T2–T4 并行，但都必须在 T7 之前完成。T7 不得提前开始。

## T0：现场基线与契约夹具（light）

依赖：无。Files：只读两仓库；Create `S/tests/fixtures/project-interview-v1/`（合成夹具，见附录 B）。

Interfaces：Consumes=本计划与设计规格；Produces=基线记录（写入实施报告第 1 节，不新增仓库文档）。

- [ ] **Step 1：记录两仓库状态**

```powershell
git -C C:\Users\27846\my-chatgpt-skills rev-parse HEAD
git -C C:\Users\27846\my-chatgpt-skills status --short
git -C C:\Users\27846\my-chatgpt-mcp-v2 rev-parse HEAD
git -C C:\Users\27846\my-chatgpt-mcp-v2 status --short
```

预期：S HEAD `7c588e4`、2 个 `M`、5 个 `??`；R HEAD `4f81009`、3 个 `??`。若不同，先记录差异与影响，只改相关任务，不覆盖用户工作。

- [ ] **Step 2：采集既有测试基线（原样保存输出与退出码）**

```powershell
cd C:\Users\27846\my-chatgpt-mcp-v2
npm test

cd C:\Users\27846\my-chatgpt-skills
python -m unittest discover -s tests -v
python -m unittest discover -s software-project-learning/tests -v
cd conducting-java-backend-mock-interviews; python -m unittest discover -s tests -v
cd ..\reviewing-java-backend-interviews; python -m unittest discover -s tests -v
```

2026-10-24 参考基线（用于判断“是否由本次引入”）：

| 套件 | 结果 |
|---|---|
| `S/tests` | 31 项通过 |
| `software-project-learning/tests` | 2 项通过 |
| `conducting-java-backend-mock-interviews/tests` | 17 项，5 项失败（断言 V1 路径/旧身份措辞） |
| `reviewing-java-backend-interviews/tests` | 12 项，1 项 error（缺 `python-docx`） |
| `R npm test` | `test:worker` 704 项全绿（约 812 s）；`test:bridge` 77 项中 2 项失败：`rds2-skill-contract.test.mjs` 仍读取已改名的 `backend-project-learning/SKILL.md`；整条命令退出码 1 |

- [ ] **Step 3：记录画像校验基线**

```powershell
cd C:\Users\27846\my-chatgpt-skills
python profile-aware-skill-creator/scripts/validate_profile_skill.py --mode profile software-project-learning
```

预期：现有 6 项失败（缺三件画像工件、未链 `references/profile-contract.md`、两处 `D:/` 路径）。这正是 T5 要修的内容。

- [ ] **Step 4：建立合成夹具占位**

创建 `S/tests/fixtures/project-interview-v1/`，放入附录 B 的场景（`scenario.json`）与 `README.md`。外层必须含 `fixtureOnly:true`，且**不是** `submit_event` DTO。具体 envoy 由 T1 据此生成；T0 不预先编造完整 envelope。

- [ ] **Step 5：负向基线**

确认当前严格合同会拒绝带新字段的 envelope：

```powershell
cd C:\Users\27846\my-chatgpt-mcp-v2
node --test services/reliable-drive-sync-worker/test/rds2-protocol.test.js
```

预期：现有测试全绿；新增字段夹具在 T1 之前无法通过（用一次性脚本或临时断言验证，不提交临时文件）。

**Done when:** 基线表、夹具路径、validator 输出都已记录，且未修改任何实现文件。
**Evidence:** 命令、退出码、输出路径、基线表。

---

## T1：严格项目合同与跨语言等价（deep）

依赖：T0。目标：JS、Python、两份 JSON Schema 对同一份 fixture 给出**一致**结论，且旧 payload 不受影响。

**Files**
- Create `R/services/reliable-drive-sync-worker/src/rds2/project-contract.js`
- Create `R/services/reliable-drive-sync-worker/test/rds2-project-contract.test.js`
- Modify `R/services/reliable-drive-sync-worker/src/protocol.js`（envelope 边界调用新校验）
- Modify `S/conducting-java-backend-mock-interviews/schemas/contracts.schema.json`
- Modify `S/reviewing-java-backend-interviews/schemas/contracts.schema.json`（与上者**逐字节一致**）
- Modify 两份 `schemas/manifest.json`（加入 `ProjectEvidence`、`ProjectAssessment`）
- Modify `S/reviewing-java-backend-interviews/scripts/interview_core.py`
- Create `S/tests/test_project_interview_contract_parity.py`

**Interfaces**
- `validateProjectQuestion(question:object):void`、`validateProjectAssessment(reviewItem:object, question:object):void`，抛带稳定 `code` 的错误。
- Python 侧同名语义：`validate_project_question(question) -> None`、`validate_project_assessment(review_item, question) -> None`。
- 纯数据校验，不联网、不读 D1。

- [ ] **Step 1：写 RED 测试（R）**

覆盖：合法 LEARN session；合法混合 MOCK；拒绝未知字段、错误 UUID、`variantAxes` 为空/超 4、`purpose=daily_recap`、`answerOrigin=assistant|synthetic`、分数超限、和≠total、`passed` 但门槛不足、`evidenceRefs` 无法定位、`assessment.attemptId` 不在 session、无 `projectEvidence` 却带 `projectAssessment`。

```js
test("a legal LEARN session validates", () => {
  assert.doesNotThrow(() => validateProjectQuestion(legalQuestion()));
});
test("daily_recap is not a recordable purpose", () => {
  assert.throws(() => validateProjectQuestion({ ...legalQuestion(), purpose: "daily_recap" }),
    (error) => error.code === "invalid_project_evidence");
});
```

- [ ] **Step 2：运行并确认 RED**

```powershell
cd C:\Users\27846\my-chatgpt-mcp-v2
node --test services/reliable-drive-sync-worker/test/rds2-project-contract.test.js
```

预期：模块不存在，失败原因正确（不是断言写错）。

- [ ] **Step 3：实现 JS 合同 + schema**

- `project-contract.js`：常量表 + 逐字段校验 + 稳定码（§5.4）。
- `protocol.js`：`projectContractVersion === 1` 时对 session/review 事件调用新校验收；否则原路径。
- 两份 schema 同步增加 `ProjectEvidence`、`ProjectAssessment` 定义，并在 `Question` / `QuestionReview` 上以 `if/then` 或显式属性接入；保持两份文件字节一致。
- `manifest.json` 两份同步加入新定义名。

- [ ] **Step 4：实现 Python 镜像**

`interview_core.py` 增加同语义校验，`create_review_event` 接受 `project_assessment` 参数（默认 `None` 保持旧签名）。`_SESSION_ID` 扩展为 `^(?:MOCK|REAL|LEARN)-[^/\\]+$`。

- [ ] **Step 5：写并跑 Python/RED→GREEN 等价测试**

```powershell
cd C:\Users\27846\my-chatgpt-skills
$env:PYTHONUTF8='1'
python -m unittest discover -s tests -p "test_project_interview_contract_parity.py" -v
```

测试必须从同一份 `tests/fixtures/project-interview-v1/` 读取用例，并断言 Python 结果、JS 校验结果（通过 `node` 子进程或生成对照表）与 JSON Schema 校验结果一致；不得只验证“能解析”。JS 一侧依赖 R 仓库：用环境变量 `RDS2_RUNTIME_ROOT` 指向 R 根；未设置或路径不存在时该用例 `skipTest("runtime_root_unavailable")`，并在报告中记为环境依赖，不伪造成通过。

- [ ] **Step 6：回归**

```powershell
cd C:\Users\27846\my-chatgpt-mcp-v2
node --test services/reliable-drive-sync-worker/test/rds2-protocol.test.js services/reliable-drive-sync-worker/test/rds2-schema-identity.test.js
cd C:\Users\27846\my-chatgpt-skills
python -m unittest discover -s tests -v
```

预期：全绿；旧 mock/real 事件仍通过。

**Done when:** 三类实现结论一致；旧负载零回归；两份 schema 字节一致。
**Evidence:** 正负向用例表、diff、schema SHA-256、命令输出。
**Review checkpoint:** 字段精确且拒绝未知值；旧合同兼容；证据引用可定位；分数与独立性不混为一谈。

---

## T2：接纳事件、项目映射与依赖（critical）

依赖：T1。目标：项目身份与 attempt 身份在接纳事务内原子登记；依赖缺失可等待、可恢复、有终止。

**Files**
- Create `R/services/reliable-drive-sync-worker/migrations/0008_rds2_interview_projects.sql`
- Create `R/services/reliable-drive-sync-worker/src/rds2/project-repository.js`
- Modify `R/services/reliable-drive-sync-worker/src/rds2/events/accept.js`
- Modify `R/services/reliable-drive-sync-worker/src/rds2/events/repository.js`（如需新查询）
- Create `R/services/reliable-drive-sync-worker/test/rds2-project-accept.test.js`
- Modify `R/tools/reliable-drive-sync-mcp/local-outbox-v2.mjs`
- Modify `R/tools/reliable-drive-sync-mcp/delivery-service-v2.mjs`
- Modify 对应测试 `test/local-outbox-v2.test.mjs`、`test/delivery-service-v2.test.mjs`
- 仅在确有新错误码需分类时修改 `src/rds2/errors/storage-error.js`

**Interfaces**
- `planProjectBindings({principal,event,existingBindings}):{bindings,errors}` 纯函数。
- `loadProjectBindings(db,userId,projectIds,basisKeys)` 有界批量读取（projectIds ≤50、basisKeys ≤50）。
- `verifyProjectReviewSource({review,session,principal}):void`：同用户、ID、题目、attempt、证据引用；session 不存在 → `source_session_not_committed`（409）。
- `resumeDependencyBlocked({requestId,sourceSessionEventId})`：Outbox 内部方法，仅在相同 envelope 重投且只读确认依赖已提交后恢复 `pending`；不开放新外部参数。

- [ ] **Step 1：写 RED 测试（竞争与越权）**

必须包含：

1. 并发首次相同 basis 绑定不同 projectId → 只接纳一个，另一个 `project_identity_conflict`。
2. 不同 session 跨项目复用 attemptId → `attempt_identity_conflict`，原行不被覆盖。
3. 跨用户引用 session → 拒绝且不泄露原文。
4. 同 requestId 同内容重试 → 只存一次（沿用现有 replay 语义）。
5. 同 eventId 不同内容 → 冲突，不换 ID 掩盖。
6. review 先到 → 409 不接纳；session 后到、同一 envelope 重投 → 成功。
7. LEARN session 落库、review 超时重启 → 恢复保持原 ID。
8. 可重试依赖错误连续 5 次 → `blocked`；同 envelope 确认依赖后 → `pending`；永久错误不可恢复。

- [ ] **Step 2：运行并确认 RED**

```powershell
cd C:\Users\27846\my-chatgpt-mcp-v2
node --test services/reliable-drive-sync-worker/test/rds2-project-accept.test.js
node --test tools/reliable-drive-sync-mcp/test/local-outbox-v2.test.mjs tools/reliable-drive-sync-mcp/test/delivery-service-v2.test.mjs
```

- [ ] **Step 3：迁移 0008（只增量）**

```sql
CREATE TABLE IF NOT EXISTS rds2_interview_projects (
  user_id TEXT NOT NULL, project_id TEXT NOT NULL,
  basis_kind TEXT NOT NULL, basis_key TEXT NOT NULL,
  display_name TEXT NOT NULL, created_event_id TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (user_id, project_id),
  UNIQUE (user_id, basis_kind, basis_key)
);
CREATE TABLE IF NOT EXISTS rds2_interview_attempts (
  user_id TEXT NOT NULL, attempt_id TEXT NOT NULL,
  project_id TEXT NOT NULL, session_id TEXT NOT NULL,
  question_id TEXT NOT NULL, source_event_id TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (user_id, attempt_id)
);
CREATE INDEX IF NOT EXISTS rds2_interview_attempts_project_idx
  ON rds2_interview_attempts (user_id, project_id, session_id);
```

- [ ] **Step 4：接入接纳事务**

- review 接纳前调用 `verifyProjectReviewSource`；失败即返回 409，不写事件、不建任务。
- `commitNewEvent` 的同一 `db.batch` 内追加项目/attempt 身份行；UNIQUE 冲突映射为稳定码并整体回滚。
- 同一 session 的幂等重放走既有 replay/alias 分支，不重复写身份行。
- 接纳仍然不发 Queue。

- [ ] **Step 5：Outbox 依赖等待与恢复**

- 新增 `source_session_not_committed` 为一类**可重试但有上限**的依赖错误：`attempt_count >= 5` 时置 `blocked` 并保留原文；其它可重试错误行为不变。
- `resumeDependencyBlocked` 只接受与 blocked 行 envelope hash 完全一致的重投；恢复后 attempt_count 归零、`available_at=now`。
- 桥接层在重投前只读调用 `interview.session.load` 或等价 D1 查询确认依赖；失败不恢复。

- [ ] **Step 6：GREEN + 扩展既有测试**

```powershell
node --test services/reliable-drive-sync-worker/test/rds2-project-accept.test.js
node --test services/reliable-drive-sync-worker/test/rds2-schema-identity.test.js services/reliable-drive-sync-worker/test/rds2-accept.test.js
node --test tools/reliable-drive-sync-mcp/test/local-outbox-v2.test.mjs tools/reliable-drive-sync-mcp/test/delivery-service-v2.test.mjs
```

**Done when:** 竞争、越权、恢复、终止四类均有真实 SQLite/Miniflare 证据；迁移可在本地隔离库重复执行。
**Evidence:** 迁移前后库表、并发测试原始输出、blocked→pending 的状态转换日志。
**Review checkpoint:** 同一请求只产生一事件；不同内容不换 ID；越权无泄漏；session 缺失不产生能力贡献。

---

## T3：有界项目归约与修订（critical）

依赖：T2。目标：项目快照可由事件确定性重建，历史增长不进入 continuation，撤回不留残影。

**Files**
- Create `R/services/reliable-drive-sync-worker/src/rds2/projection/project-interview.js`
- Modify `src/rds2/projection/interview.js`、`builds.js`、`staging-read.js`、`commit.js`
- Modify `src/rds2/archive/replay-validate.js`、`archiver.js`
- Create `test/rds2-project-interview.test.js`、`test/rds2-project-build-v2.test.js`
- Modify 既有 `test/rds2-interview.test.js`、`test/rds2-projection-engine.test.js`

**Interfaces**
- 纯函数 `reduceProjectAttempts({sessions,selectedReviews}):{attempts,summaries,weaknesses}`（oracle 与小样本用）。
- 生产入口 `planProjectPageReads({events,continuation}):{reads,ranges}`、`buildProjectPage({events,staged,continuation}):{rowChanges,continuation}`，经 `interviewReducer` 原入口分派到 v2 分支。
- 新 range：`{rowKind:"project_attempt", after:[sortKey,rowKey]|null, limit:1..20}`，与点读共享 4 次调用预算。

- [ ] **Step 1：写 RED（行为规则）**

- 撤回旧通过后不再 closed（`review_replacement_removes_old_pass_contributions`）。
- 两 session 同 variant 不关闭；不同 variant 同 exposureGroup 不关闭；两者都不同才 closed。
- 新有效 failed 重开周期，旧通过不跨周期。
- 同日多次真实尝试各自保留。
- 有提示 / 已看过原答案 / `user_recall` 不算独立通过。
- `apply=false` 不撤旧；`apply=true` 的 `unscored` 撤回。
- 乱序、分批回放与一次性回放等价。

- [ ] **Step 2：写 RED（有界性）**

- 50+ 项目、单场 10+ 题、每题多弱点。
- 单事件拆多子页；崩溃恢复；分页边界；单条大答题。
- 断言每页 ≤20 rowChanges、≤4 次读、单行 ≤64 KiB、包 ≤256 KiB。
- 断言 continuation 大小不随历史线性增长。
- 新 envelope 48 KiB / 题 24 KiB / 评价 8 KiB 超限被明确拒绝。
- 摘要 `coverage`/ID 列表裁剪后计数仍为全量，并带 `truncated`。

- [ ] **Step 3：运行并确认 RED**

```powershell
cd C:\Users\27846\my-chatgpt-mcp-v2
node --test services/reliable-drive-sync-worker/test/rds2-project-interview.test.js
node --test services/reliable-drive-sync-worker/test/rds2-project-build-v2.test.js
```

- [ ] **Step 4：实现 ingest → fold_attempts**

- 新行 kind：`project_attempt`、`project_summary`、`project_weakness`，内部 `project_selected_review`、`project_review_question`。
- continuation `{buildContractVersion:2,phase,nextEventSeq,eventItemIndex,rangeAfter,foldItemIndex,page}`；严格单调校验。
- `staging-read.js` 增加 range read；`builds.js` 的合并逻辑改为按实际 kind 集合合并（不再写死四桶）。
- fold 结束后才 activation；`apply=false` 的 review 只入 `review` 行，不改变选中指针。
- 贡献排序：`(completedAt UTC ms, sessionId, question index 补零, attemptId)`。

- [ ] **Step 5：归档 v2 与离线校验**

- `build_package` 增加 `buildContractVersion:2`、`workStart/workEnd`、`sourceEventHash`、`frozenTarget`。
- `replay-validate` 对 v2 拒绝：缺页、重复子项、跳项、非法零进展、fold 未完成即激活；v1 仍按旧规则。
- 离线回放产出与在线投影逐行一致（同一 oracle 比较）。

- [ ] **Step 6：GREEN + 回归**

```powershell
node --test services/reliable-drive-sync-worker/test/rds2-project-interview.test.js
node --test services/reliable-drive-sync-worker/test/rds2-project-build-v2.test.js
node --test services/reliable-drive-sync-worker/test/rds2-interview.test.js services/reliable-drive-sync-worker/test/rds2-projection-engine.test.js services/reliable-drive-sync-worker/test/rds2-archive.test.js
```

**Done when:** oracle 与分批生产路径在小样本与大样本上结果一致；旧域测试全绿；continuation 大小有实测数字。
**Evidence:** oracle 对照表、分页与 continuation 字节数、包大小、乱序回放对比。
**Review checkpoint:** 无旧贡献残留；不能伪造独立通过；legacy 回归通过；大历史不进 continuation。

---

## T4：项目过滤查询与 feature 握手（critical）

依赖：T3。目标：项目视图可按项目分页读取，过滤在 SQL 内，cursor 绑定完整过滤条件。

**Files**
- Modify `R/shared/rds2-protocol.mjs`（`validateQuery` 的 `projection.read` 允许 `projectId`、`rowKind`）
- Modify `R/services/reliable-drive-sync-worker/src/rds2/query.js`
- Modify `R/services/reliable-drive-sync-worker/src/rds2/routes.js`（仅在需要显式错误映射时）
- Create `R/services/reliable-drive-sync-worker/test/rds2-project-query.test.js`
- Modify `R/tools/reliable-drive-sync-mcp/test/v2-routing.test.mjs`（确认 DTO 直传仍成立）

**Interfaces**
- 扩展既有 `projection.read` DTO；**不新增工具、不新增事件类型**（`{"storageVersion":2,"operation":"projection.read","params":{…}}` 已被桥接层原样转发）。
- `capabilities.features.interviewProjectSnapshots={version:1,projectFilter:true}`。
- 返回沿用 `revision/building/lastEventSeq/entries/nextCursor`，`summary` 受项目范围限制。

- [ ] **Step 1：写 RED**

- `project_cursor_is_bound_to_filters_and_principal`：改动 projectId、rowKind、用户、namespace 或 revision 均拒绝。
- 只读本项目行：构造两个项目，断言响应 entries 的 `member_key` 全为请求项目。
- `summary` 只含该项目摘要，不含全局或其它项目。
- 目录查询（`rowKind=project_summary` 且无 projectId）只返回摘要元数据。
- `building=true` 不解释为 0。
- `project_attempt` / `project_weakness` 无 projectId → `invalid_params`。
- 旧查询行为不变（legacy kind、全局 summary）。
- `LEARN-` session 只能被同用户 `interview.session.load` 读到。

- [ ] **Step 2：运行并确认 RED**

```powershell
cd C:\Users\27846\my-chatgpt-mcp-v2
node --test services/reliable-drive-sync-worker/test/rds2-project-query.test.js
```

- [ ] **Step 3：实现**

- `requirePageScope` 允许 `projectId`、`rowKind`；`projectId` 必须 UUID，且限 `interview/interview`。
- SQL 增加 `AND (? IS NULL OR member_key = ?)`；`rowKind` 白名单：`project_summary|project_attempt|project_weakness`。
- cursor payload 增加 `pid`，`f` 与实际 rowKind 必须一致；解码后逐项比对，不一致 → `cursor_scope_mismatch`。
- 项目查询的 `summary` 从 `project_summary` 行读取；无行返回 `null`。
- capabilities 增加 feature，仅在实现完成后默认开启；环境开关允许关闭。

- [ ] **Step 4：GREEN + 回归**

```powershell
node --test services/reliable-drive-sync-worker/test/rds2-project-query.test.js
node --test services/reliable-drive-sync-worker/test/rds2-routes.test.js services/reliable-drive-sync-worker/test/rds2-staging-read.test.js
node --test tools/reliable-drive-sync-mcp/test/v2-routing.test.mjs
```

**Done when:** 负向隔离用例全部拒绝；旧查询字节行为不变；响应 ≤256 KiB。
**Evidence:** SQL 参数隔离断言、响应字节数、cursor 篡改用例。
**Review checkpoint:** 过滤在 SQL 生效；summary 不泄漏；cursor 绑定完整；feature 只在就绪后声明。

---

## T5：项目学习的讲解、回顾与问答交接（deep）

依赖：T1。可在未连云的夹具模式完成。目标：输出达到已认可的教学效果，回顾零写入，正式问答可交接。

**Files**
- Modify `S/software-project-learning/SKILL.md`、`README.md`
- Modify `references/standard-mode.md`、`interview-mode.md`、`detailed-lesson-format.md`、`rds-v2-runtime.md`
- Create `references/project-evidence-contract.md`
- Create `references/examples/ticket-query-rds-complete-dialogue.md`
- Create `references/examples/assets/` 三张时序图（PNG）
- Create `references/profile-contract.md`、`schemas/profile-capability.json`、`tests/test_profile_contract.py`
- Create `scripts/project_evidence.py`、`tests/test_project_evidence.py`
- Modify `tests/behavior-scenarios.md`
- 必要时同步 `references/copy-paste-prompt.md` 的冲突条目

**Interfaces**
- `build_learning_session(identity, questions, *, session_id, event_id, started_at, completed_at) -> dict`
- `build_outline_event(identity, *, project_id, unit_id, outline, observed_at, event_id) -> dict`
- `classify_turn(context: dict) -> "recap" | "teaching" | "formal_qa"`
- `prepare_review_handoff(session, assessments, *, review_event_id, review_version, completed_at) -> dict`
- 前两者纯构造：不发 HTTP、不生成 ID、不写快照。

- [ ] **Step 1：写 RED**

- `test_recap_produces_no_assessment_or_outline_write`：回顾输入只得到 `"recap"`，构造器不产生 session/outline。
- 教学 outline 只有 `observed`；`confidence=high` 只表示已讲授。
- 合成/教练答案被拒绝为能力事件。
- 同题提示保留首答（`timeline` 追加而非替换）。
- 没有用户作答时不构造 session。
- 缺 feature 时只教学 + 本地待交接，不发新合同云写。

- [ ] **Step 2：跑 RED**

```powershell
cd C:\Users\27846\my-chatgpt-skills
$env:PYTHONUTF8='1'
python -m unittest discover -s software-project-learning/tests -v
```

- [ ] **Step 3：重构入口为短路由**

`SKILL.md` 保持路由与硬约束，详细规则移入 references；`project-evidence-contract.md` 是唯一问答合同来源，`profile-contract.md` 链接它，避免两份规则。新增完整对话样例，按“场景 → 图 → 源码节选 → 状态与反例 → 取舍 → 口述答案 → 底部一道题”组织。

- [ ] **Step 4：补齐画像工件**

- `references/profile-contract.md`：domain `backend-project-learning`、sourceSkill `software-project-learning`、`learning-outline` 仅 `observed`、记录条件与禁止项。
- `schemas/profile-capability.json`：按仓库 schema 填写 `dimensions`/`evidencePolicy`/`runtime`/`portability`，`runtime` 常量必须与 validator 一致。
- `tests/test_profile_contract.py`：≥4 项，覆盖四个 contract behavior（能力声明、记录条件、排除条件、运行时入口）。
- 去掉两处 `D:/` 硬编码，改为 `<project-root>/…` 占位；真实输出时再给绝对路径。validator 扫描技能目录内**所有**文件，新增样例、README、PNG 同目录的说明文字都不得出现盘符路径。

- [ ] **Step 5：GREEN + validator + 输出演练**

```powershell
python -m unittest discover -s software-project-learning/tests -v
python profile-aware-skill-creator/scripts/validate_profile_skill.py --mode profile software-project-learning
```

预期：`OK: software-project-learning passes profile validation`。

- [ ] **Step 6：实际模型轨迹（L 组）**

用隔离合成输入跑 L01–L10，保存逐轮消息与来源标注；图片必须可见，源码行号必须与 E 仓库当前工作树一致。确定性测试与模型行为评估分开报告。

**Done when:** 测试与 validator 全绿；L 组每条有轨迹；样例未写入任何个人 RDS。
**Evidence:** diff、validator 输出、L 组轨迹、图片文件与哈希。
**Review checkpoint:** 图可见且源码忠实；回顾无旁路写入；提示不覆盖原答；无用户回答不制造分数；有幽默但不牺牲准确。

---

## T6：简历项目选题、专项复测与复盘联动（deep）

依赖：T1。目标：专项只围绕选中项目；完整 mock 配比不变；复盘合同贯通。

**Files**
- Modify `S/conducting-java-backend-mock-interviews/SKILL.md`、`references/interview-protocol.md`、`candidate-profile-integration.md`、`report-rubric.md`、`rds-v2-runtime.md`
- Modify `scripts/mock_handoff.py`、`tests/test_mock_handoff.py`、`tests/test_cross_skill_contract.py`
- Create `references/project-targeted-interview.md`、`references/web-question-sourcing.md`
- Create `scripts/project_question_plan.py`、`tests/test_project_question_plan.py`
- Modify `S/reviewing-java-backend-interviews/SKILL.md`、`references/review-protocol.md`、`shared-interview-system-design.md`（受影响条目）
- Modify `scripts/create_review_report.py` 及相关测试（仅为 LEARN/type/项目证据显示）

**Interfaces**
- `build_question_plan({mode,projectId,resumeClaims,snapshot,candidates,budget}) -> {selected,rejected,warnings}`：纯选择约束器；候选语义由模型产生。
- `create_mock_session_event(..., mode="full_mock", project_contract_version=None)`：保留旧签名；专项显式跳过 40% 弱点上限，但仍校验项目一致。

- [ ] **Step 1：写 RED**

- `targeted_mode_can_use_all_project_weaknesses_without_changing_full_mock`。
- 无简历不伪造 claim；A 项目不会选到 B 弱点。
- 转载与原帖合并 `originGroupId`。
- 仅换数字/人名不产生新 variant；改变故障模型才可新 variant。
- 网络中断不编造出处，标 `frequency=unknown`。
- mock 本题作答前不泄露答案；最多一次提示。

- [ ] **Step 2：跑 RED**

```powershell
cd C:\Users\27846\my-chatgpt-skills\conducting-java-backend-mock-interviews
$env:PYTHONUTF8='1'
python -m unittest discover -s tests -v
```

- [ ] **Step 3：实现选择约束与模式**

- `full_mock`：55/15/10/20（无简历 35/45/20），弱点 ≤40%。
- `project_targeted`：全部候选必须属于 `projectId`；允许一题基础机制；不参与 40% 计算。
- 候选卡字段与来源卡字段按设计 §8.5；`originGroupId` 去重。
- session 构造支持 `project_contract_version=1` 与 `LEARN-` 前缀，复用 T1 校验，不复制规则。

- [ ] **Step 4：复盘联动**

`interview_core.create_review_event` 支持 `project_assessment`，evidenceRefs 校验指向真实题目/消息；`project_learning` 强制 `profile_changes=[]`。

- [ ] **Step 5：处理既有失败（B3）**

5 项陈旧断言改为 V2 现状（`outputs/interview/<userId>/interview-<sessionId>-session.json` 等），并在报告中单独标注“既有失败修复”，不删除测试。

- [ ] **Step 6：GREEN + Q 组演练**

```powershell
python -m unittest discover -s tests -v
cd ..\reviewing-java-backend-interviews
python -m unittest discover -s tests -v    # 若缺 python-docx，记为 blocked_environment
```

输出 Q01–Q10 的实际轨迹：每题选中理由、来源、剔除理由、答题前后边界。

**Done when:** 两组 Python 套件状态明确（通过或环境阻塞）；Q 组有实际证据。
**Evidence:** diff、测试输出、候选卡样例、对话轨迹。
**Review checkpoint:** 简历未确认不认领；网络线索不当技术答案；专项与完整配比互不影响；一题一等；复盘唯一 owner。

---

## T7：隔离集成、归档回放与交回（deep）

依赖：T3、T4、T5、T6。目标：端到端只含正式证据；在线与离线一致；交付可复核。

**Files**
- Create `R/services/reliable-drive-sync-worker/test/rds2-project-e2e.test.js`
- Modify `R/services/reliable-drive-sync-worker/test/rds2-archive.test.js`
- Modify `R/tools/reliable-drive-sync-mcp/test/rds2-skill-contract.test.mjs`（既有失败 B7）
- Create `S/tests/test_project_learning_interview_flow.py`
- 更新受影响 README 与安装文件清单（不写安装缓存）

- [ ] **Step 1：先写失败的端到端测试**

流程：教学提纲（observed）→ A1 session + review（open）→ 次日回顾（0 写入，快照不变）→ A2 新条件无提示（improving）→ A3 另一变式/曝光组（closed）→ A2 review v2 `unscored`（回 improving）→ 离线回放逐行一致。中途插入网络超时与 review 乱序。

- [ ] **Step 2：RED → 仅补集成缺口**

不得为通过测试放宽 DTO 或上限。

- [ ] **Step 3：GREEN + 全量回归**

```powershell
cd C:\Users\27846\my-chatgpt-mcp-v2
npm test     # 记录最终退出码
cd C:\Users\27846\my-chatgpt-skills
$env:PYTHONUTF8='1'
python -m unittest discover -s tests -v
python -m unittest discover -s software-project-learning/tests -v
cd conducting-java-backend-mock-interviews; python -m unittest discover -s tests -v
cd ..\reviewing-java-backend-interviews; python -m unittest discover -s tests -v
cd ..; python profile-aware-skill-creator/scripts/validate_profile_skill.py --mode profile software-project-learning
```

- [ ] **Step 4：填 44 项验收表**

逐项 `pass/fail/blocked/not_run`，附命令、退出码、证据路径。未运行不得写 pass。

- [ ] **Step 5：修正既有跨仓库合同失败（B7）**

`rds2-skill-contract.test.mjs` 把 `backend-project-learning/SKILL.md` 改为 `software-project-learning/SKILL.md`，并核对断言语义：`默认只读学习` 等句子若在 T5/T6 已改写，按新合同更新断言，保留原意（只读、源码事实、一次一题、原答不改、唯一 submit_event）。修复前先记录 2 项失败原文，修复后断言 77 项全绿（或说明用例数变化原因）。

- [ ] **Step 6：出具完整教学输出的实际运行版**

图可见、源码行号、注释忠实、单题等待、帮助标记逐项检查。

**Done when:** P0 全部通过、P1 无未说明缺口、离线与在线一致。
**Evidence:** 端到端日志、44 项表、实际输出、哈希清单。

## 交回物

1. 两仓库精确基线、变更文件清单与完整 diff（含新增目录、schema、图片）。
2. T0 基线日志、各任务 RED/GREEN 原始输出、全套回归退出码；既有失败与本次新失败分开。
3. 44 项验收表（真实状态 + 证据路径）。
4. 一份达到设计 §8.1 的实际输出（图、源码、追问）。
5. 隔离测试证据：D1 迁移、Outbox 恢复、身份/项目隔离、v2 子页、新旧归档回放。
6. 实施报告：已验证、未运行、阻塞、已知限制、文件 SHA-256；不得写“全部完成”而无证据。
7. 待用户提交的文件列表；不执行 commit/push/部署/安装。

## 附录 A：44 项验收矩阵

| ID | 优先级 | 观察点 | 任务 |
|---|---|---|---|
| L01 | P1 | 原创场景、可见时序图、源码与口述答案；不强制先答题 | T5 |
| L02 | P0 | 保留变量/条件，省略标注；逻辑与修复建议分开 | T5 |
| L03 | P0 | 分清 Redis 与局部 Map；静态推导不称并发实测 | T5 |
| L04 | P1 | 注释解释目的/输入/状态/返回；笑点不替代因果 | T5 |
| L05 | P0 | 用户未答时停止，无伪造答案、无 session/review | T5 |
| L06 | P0 | “不会”+提示：保留首答，补答同 attempt，非独立通过 | T5 |
| L07 | P0 | 次日回顾：0 业务写，0 attempt/review/outline | T5 |
| L08 | P0 | 多项目/午夜边界：按 Asia/Shanghai 选昨日，只还原已教内容 | T5 |
| L09 | P0 | 投影缺失/构建中：历史未知，不当 0 | T4/T5 |
| L10 | P0 | 只讲未答可记 outline=observed；合成答案拒绝 | T1/T5 |
| Q01 | P0 | 简历 claim 已确认；源码功能不冒充个人贡献 | T6 |
| Q02 | P0 | 缺简历：标明非简历定制，不造经历 | T6 |
| Q03 | P0 | 只考 12306：不混其它项目弱点 | T6 |
| Q04 | P0 | 专项可全弱点；完整 mock 40% 与配比不变 | T6 |
| Q05 | P1 | 原帖/转载同 originGroup；日期不明为 null | T6 |
| Q06 | P0 | 搜索摘要与官方冲突：以源码/官方校正 | T6 |
| Q07 | P0 | 联网不可用/历史帖：标局限与 frequency unknown | T6 |
| Q08 | P0 | L1–L4 递进，无虚构录用线 | T6 |
| Q09 | P0 | 未答不泄答案；最多一次提示 | T6 |
| Q10 | P0 | 换数字≠新变式；改故障模型才可新 variant | T3/T6 |
| R01 | P0 | 合同正负夹具 JS/Python/schema 等价 | T1 |
| R02 | P0 | 旧 mock/real 合同、helper、summary、回放不变 | T1/T3/T7 |
| R03 | P0 | 缺 feature/身份不匹配：不发新字段，普通教学可继续 | T4/T5 |
| R04 | P0 | 跨用户引用：拒绝且不泄露 | T2/T4 |
| R05 | P0 | 并发 basis 绑定：只接纳一致绑定 | T2 |
| R06 | P0 | 复用 attemptId：冲突，不覆盖 | T2 |
| R07 | P0 | 重试只一次；同 ID 改内容冲突 | T2 |
| R08 | P0 | session 已入库、review 超时：待评估，原 ID 恢复 | T2/T5/T7 |
| R09 | P0 | review 先到：409；5 次 blocked；确认依赖后恢复 | T2 |
| R10 | P0 | 引用错 question/attempt/source：拒绝 | T1/T2 |
| R11 | P0 | 提示/看过答案/回忆：不可独立通过 | T3 |
| R12 | P0 | 两独立通过才 closed；同日不去重 | T3 |
| R13 | P0 | passed 后新 failed：重开周期 | T3 |
| R14 | P0 | 高版本撤回；apply=false 不撤旧；乱序一致 | T3 |
| R15 | P0 | 项目贡献不重复进 legacy profileChanges | T1/T3/T6 |
| R16 | P0 | 项目过滤 + cursor 篡改：SQL 过滤，summary 隔离 | T4 |
| R17 | P0 | 10+ 题/50+ 项目：每页 20 changes/4 reads，fold 完才切代 | T3 |
| R18 | P0 | 崩溃/重复唤醒：guard/lease/CAS 一次推进 | T3/T7 |
| R19 | P0 | v2 包非法拒绝；v1 仍可回放；在线=离线 | T3/T7 |
| R20 | P0 | 48/24/8 KiB 超限拒绝；摘要 truncated + 总量 | T1/T3 |
| P01 | P0 | 四阶段不混；event.status 沿原 ID | T5/T7 |
| P02 | P0 | 用户 dirty 保留；diff 与基线准确 | T0/T7 |
| P03 | P1 | UTF-8、链接有效、三张图可见、完整目录与哈希 | T7 |
| P04 | P0 | 所有用例真实状态；未运行不称 pass；无擅自提交 | T7 |

## 附录 B：最小合成夹具

`tests/fixtures/project-interview-v1/scenario.json` 必须 `fixtureOnly:true`，且**不是** `submit_event` DTO；仅用于隔离本地测试。

```json
{
  "fixtureOnly": true,
  "identity": {"userId": "22222222-2222-4222-8222-222222222222", "username": "隔离演示学员"},
  "project": {
    "projectId": "11111111-1111-4111-8111-111111111111",
    "displayName": "12306",
    "basis": {"kind": "source_learning", "key": "source-learning:train-12306:local-verified"},
    "resumeVersion": null, "resumeClaimIds": [], "sourceRevision": "worktree:2026-10-23"
  },
  "sessions": [
    {"sessionId": "LEARN-20261023T020000Z-44444444-4444-4444-8444-000000000001", "completedAt": "2026-10-23T02:08:00Z",
     "attemptId": "33333333-3333-4333-8333-000000000001", "variantId": "waiter-return",
     "purpose": "initial_assessment",
     "provenance": {"answerOrigin": "actual_user", "assistance": "hint",
                    "exactAnswerSeenBefore": true, "exposureGroupId": "exposure-20261023"},
     "outcome": "partial", "total": 62},
    {"sessionId": "MOCK-20261024T020000Z-44444444-4444-4444-8444-000000000002", "completedAt": "2026-10-24T02:05:00Z",
     "attemptId": "33333333-3333-4333-8333-000000000002", "variantId": "write-timeout-result-unknown",
     "purpose": "targeted_retest",
     "provenance": {"answerOrigin": "actual_user", "assistance": "none",
                    "exactAnswerSeenBefore": false, "exposureGroupId": "exposure-20261024"},
     "outcome": "passed", "total": 88},
    {"sessionId": "MOCK-20261025T020000Z-44444444-4444-4444-8444-000000000003", "completedAt": "2026-10-25T02:05:00Z",
     "attemptId": "33333333-3333-4333-8333-000000000003", "variantId": "hash-exists-field-missing",
     "purpose": "targeted_retest",
     "provenance": {"answerOrigin": "actual_user", "assistance": "none",
                    "exactAnswerSeenBefore": false, "exposureGroupId": "exposure-20261025"},
     "outcome": "passed", "total": 90}
  ],
  "revision": {"targetSession": "MOCK-20261024T020000Z-44444444-4444-4444-8444-000000000002", "reviewVersion": 2, "outcome": "unscored", "scores": null},
  "recap": {"simulatedDate": "2026-10-24", "expectedBusinessWrites": 0, "expectedAttemptsAdded": 0},
  "expectedTransitions": ["open", "open", "improving", "closed", "improving"]
}
```

期望：`open →（回顾不变）→ improving → closed →（撤回）improving`。

## 附录 C：风险与停止条件

| 风险 | 处理 |
|---|---|
| 构建引擎改动破坏其它域 | 只走 interview v2 分支；旧域全量回归；不满足则停止并回退该分支 |
| 迁移在已有数据上失败 | 只用增量 `CREATE TABLE/INDEX IF NOT EXISTS`；本地先跑两次 |
| 依赖恢复被滥用为“改 ID 重提” | 恢复要求 envelope hash 完全一致；永久错误不恢复 |
| 合同三实现漂移 | T1 的等价测试为强制门；schema 字节一致 |
| 模型行为不可复现 | L/Q 组保留逐轮消息与合成输入标注，结论只针对记录版本 |
| 全量 `npm test` 超时 | 记录已跑部分与最终退出码；未完成项写 `not_run` |
| 既有失败被误算 | 先基线后改动；报告分列“既有”“新引入”“已修复” |

停止条件：出现需要改变本设计才能继续的冲突时，先改规格与本计划，再实施；不得在代码里私自定义合同。
