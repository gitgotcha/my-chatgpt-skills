# 简历八股技能与全域存储规范化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新建 `java-knowledge-based-on-resume-learn-skill`，并将算法学习、模拟面试、面试复盘及 Cloud MCP 全量迁移到 `DriveRoot/my-chatGPT-skills/` 下的全局用户与领域目录契约。

**Architecture:** `submit_event` 是唯一云端写入口。Worker 先按标准化姓名在全局注册表解析或创建稳定 `userId`，再把不可变事件写入 `users/<userId>/<domain>/events/`，最后由领域 reducer 物化快照或当日题单。旧 namespace 目录只由只读兼容器和迁移器访问；迁移采用 dry-run、内容哈希校验和非破坏性复制。

**Tech Stack:** Markdown skills、JSON Schema Draft 2020-12、Python 3 `unittest`、Node.js ESM `node:test`、Cloudflare Worker、Google Drive API、MCP `submit_event`。

**Spec:** [`docs/superpowers/specs/2026-08-29-java-resume-knowledge-design.md`](../specs/2026-08-29-java-resume-knowledge-design.md)

## Global Constraints

- 所有云端写入只允许经 `submit_event`；Skill、定时任务模板和 Python 辅助脚本不得直接写 Drive。
- 唯一规范根是 `DriveRoot/my-chatGPT-skills/`。不得继续创建 namespace 级 `algorithm/user-registry`、`algorithm/users`、`interview/user-registry` 或 `interview/users`。
- 姓名只做 NFKC 与首尾空白标准化。相同 `nameKey` 返回同一 `userId`；不同姓名生成独立 ID；无法消解的同名冲突必须停止。
- 旧数据不移动、不覆盖、不删除。旧路径只允许出现在 `legacy-reader`、迁移实现、迁移测试或明确标记为 archived/superseded 的历史文档中。
- `outputs/interview/<userId>/` 是本地可移植副本，不是云端画像输入，不纳入 Drive 目录迁移。
- 保留既有 schema-1.2 事件的可读性；新增事件同样使用 `schemaVersion: "1.2"`，除非实现期间先单独修订并批准设计规范。
- 定时任务由用户自行创建；本计划不创建或修改自动化任务。
- 每个任务遵循红—绿—重构：先写失败测试并确认失败原因，再实现最小代码，最后运行相关测试并提交。

---

## Task 1: 建立规范目录构造器与全局用户注册

**Files:**

- Create: `cloud-mcp/src/storage-layout.js`
- Create: `cloud-mcp/src/user-store.js`
- Create: `cloud-mcp/test/storage-layout.test.js`
- Create: `cloud-mcp/test/user-store.test.js`
- Modify: `cloud-mcp/src/google-drive.js`
- Delete after migration: `cloud-mcp/src/namespace-store.js`
- Delete after migration: `cloud-mcp/test/namespace-store.test.js`

- [ ] 编写 `storage-layout.test.js`，锁定唯一父子链：

```js
test("algorithm events use the canonical plugin root", async () => {
  const folder = await layout.ensureDomainPath(USER_ID, "algorithm", ["events"]);
  assert.deepEqual(ancestry(folder.id), [
    "root", "my-chatGPT-skills", "users", USER_ID, "algorithm", "events"
  ]);
});

test("domain creation never creates a namespace registry", async () => {
  await layout.ensureDomainPath(USER_ID, "interview", ["events"]);
  assert.equal(findPath("root/algorithm/user-registry"), undefined);
  assert.equal(findPath("root/interview/user-registry"), undefined);
});
```

- [ ] 编写 `user-store.test.js`，覆盖 NFKC/trim、同名幂等、不同姓名不同 ID、缺失用户创建、重复注册文件冲突和错误父目录拒绝。

```js
assert.equal(normalizeDisplayName("  Ａda  "), "Ada");
assert.equal((await store.resolveOrCreate({ displayName: "乔炳源" })).userId, USER_ID);
assert.equal((await store.resolveOrCreate({ displayName: " 乔炳源 " })).userId, USER_ID);
await assert.rejects(() => store.resolveOrCreate({ displayName: "" }), /invalid_display_name/);
```

- [ ] 运行并确认测试因模块不存在而失败：

```bash
cd cloud-mcp
node --test test/storage-layout.test.js test/user-store.test.js
```

Expected: `ERR_MODULE_NOT_FOUND`。

- [ ] 实现 `createStorageLayout({ drive, pluginRootName = "my-chatGPT-skills" })`，只暴露受控方法：

```js
layout.ensureBase()
layout.findBase()
layout.ensureUserRoot(userId)
layout.findUserRoot(userId)
layout.ensureDomainPath(userId, domain, segments)
layout.findDomainPath(userId, domain, segments)
```

只允许 `algorithm | interview | resume-knowledge` 领域和设计规范中的叶目录；拒绝 `/`、`\\`、`.`、`..` 及未知段。

- [ ] 实现 `normalizeDisplayName` 与 `createUserStore({ layout, drive, now, uuid })`：

```js
userStore.listRegistrations()
userStore.resolveOrCreate({ displayName, preferredUserId })
userStore.verify({ userId, displayName })
```

注册顺序为：创建/确认全局用户目录 → 创建并读回 `identity.json` → 创建并读回 `registration-<userId>.json`。注册文件是最后的可见提交点。

- [ ] 扩展 `google-drive.js` 的 JSON 文件名白名单，允许 `daily-plan-*`、`resume-*`、`question-bank-*` 与 `migration-*`，同时继续拒绝路径分隔符和非 JSON 文件。

- [ ] 将旧 `namespace-store.js` 的只读职责留给 Task 3 的 legacy adapter；完成调用方迁移后删除该模块及旧测试。

- [ ] 运行测试：

```bash
cd cloud-mcp
node --test test/google-drive.test.js test/storage-layout.test.js test/user-store.test.js
```

Expected: all pass。

- [ ] Commit:

```bash
git add cloud-mcp/src/storage-layout.js cloud-mcp/src/user-store.js cloud-mcp/src/google-drive.js cloud-mcp/test/storage-layout.test.js cloud-mcp/test/user-store.test.js
git commit -m "feat: add canonical storage layout and global user registry"
```

## Task 2: 改造 `submit_event` 的姓名绑定与协议分发

**Files:**

- Modify: `cloud-mcp/src/protocol.js`
- Modify: `cloud-mcp/src/submit-event.js`
- Modify: `cloud-mcp/src/index.js`
- Modify: `cloud-mcp/test/mcp.test.js`
- Modify: `cloud-mcp/test/end-to-end.test.js`

- [ ] 先在 `mcp.test.js` 增加失败测试：允许 `system`、`resume-knowledge` namespace；支持 `system.user-registered`；业务事件可以用姓名解析用户；未知姓名自动创建；姓名和已有 `userId` 不匹配时拒绝。

```js
const registered = validateEnvelope({
  schemaVersion: "1.2",
  namespace: "system",
  eventType: "system.user-registered",
  payload: { displayName: "乔炳源" },
  requestId: "register-1"
});
assert.equal(registered.payload.displayName, "乔炳源");
```

- [ ] 运行目标测试并确认当前因 `invalid_namespace` 或 `invalid_event_type` 失败：

```bash
cd cloud-mcp
node --test test/mcp.test.js
```

- [ ] 在 `protocol.js` 中声明完整事件集合：

```text
system.user-registered
system.legacy-migration-requested
algorithm.learning.completed
algorithm.daily-plan-created
interview.session.list
interview.session.load
interview.session.completed
interview.review.completed
resume-knowledge.resume-ingested
resume-knowledge.claim-confirmed
resume-knowledge.claim-rejected
resume-knowledge.question-bank-created
resume-knowledge.daily-plan-created
resume-knowledge.answer-scored
```

保留严格 envelope 字段检查。`identity` 接受 `{username, userId?}`；事件进入具体 schema 校验前，由 Worker 用全局注册结果补齐并锁定 `userId`/规范化姓名。已提供身份与注册不一致时返回 `identity_mismatch`。

- [ ] 在 `submit-event.js` 中用单例 `userStore` 替换 namespace store map。实现内部绑定顺序：提取姓名 → `resolveOrCreate` → 校验可选 `userId` → 向事件草稿补齐身份 → 具体事件校验 → 领域 handler。

- [ ] `system.user-registered` 只物化全局注册和用户根；业务事件首次使用未知姓名时复用同一 `resolveOrCreate`，因此也能自动注册。响应始终返回规范化的 `identity`。

- [ ] 更新 `index.js` 的工具描述和 input schema：仍只暴露 `submit_event`，但不再把 `userId` 设为姓名解析前的必填字段。

- [ ] 更新端到端测试为“按姓名注册/解析 → 提交业务事件”，并证明算法与面试调用得到同一个 `userId`。

- [ ] 运行：

```bash
cd cloud-mcp
node --test test/mcp.test.js test/end-to-end.test.js test/user-store.test.js
```

Expected: all pass。

- [ ] Commit:

```bash
git add cloud-mcp/src/protocol.js cloud-mcp/src/submit-event.js cloud-mcp/src/index.js cloud-mcp/test/mcp.test.js cloud-mcp/test/end-to-end.test.js
git commit -m "feat: resolve submit events through the global user registry"
```

## Task 3: 将事件存储切换到用户领域目录，并隔离旧路径读取

**Files:**

- Modify: `cloud-mcp/src/event-store.js`
- Create: `cloud-mcp/src/legacy-reader.js`
- Modify: `cloud-mcp/test/event-store.test.js`
- Create: `cloud-mcp/test/legacy-reader.test.js`
- Delete: `cloud-mcp/src/namespace-store.js`
- Delete: `cloud-mcp/test/namespace-store.test.js`

- [ ] 在 `event-store.test.js` 中把期望 ancestry 改为：

```text
root/my-chatGPT-skills/users/<userId>/<domain>/events/event-<eventId>.json
```

并增加断言：即使规范路径写入失败，也没有针对 `root/algorithm/...` 或 `root/interview/...` 的 `ensureFolder/createJson` 调用。

- [ ] 编写 `legacy-reader.test.js`：规范目录有数据时不读旧目录；规范目录缺失时只读 `algorithm/users/<userId>/...` 或 `interview/users/<userId>/...`；该模块对象上不存在 create/update/delete 方法。

- [ ] 运行测试，确认仍看到旧 namespace ancestry：

```bash
cd cloud-mcp
node --test test/event-store.test.js test/legacy-reader.test.js
```

- [ ] 将 `createEventStore` 改为：

```js
createEventStore({ domain, userStore, layout, drive, legacyReader, canonicalHash })
```

`appendEvent` 只使用 `layout.ensureDomainPath(userId, domain, ["events"])`；`listVerifiedEvents` 使用规范路径优先、旧路径回退。事件键冲突、内容哈希、文件父目录和身份校验行为保持不变。

- [ ] 实现 `createLegacyReader({ drive })`，显式列出允许读取的旧 registration/event/snapshot 路径。任何传入 `create: true`、未知路径或写方法请求都抛出 `legacy_read_only`。

- [ ] 删除不再被引用的 namespace store 和测试，用 `rg` 确认运行时代码不再创建 namespace 注册表：

```bash
rg -n 'createNamespaceStore|ensureFolder\(drive\.rootFolderId, namespace\)' cloud-mcp/src cloud-mcp/test
```

Expected: no matches。

- [ ] 运行：

```bash
cd cloud-mcp
node --test test/event-store.test.js test/legacy-reader.test.js test/mcp.test.js
```

- [ ] Commit:

```bash
git add -A cloud-mcp/src cloud-mcp/test
git commit -m "refactor: store all domain events below canonical user roots"
```

## Task 4: 补齐算法快照/题单并规范化面试快照

**Files:**

- Create: `cloud-mcp/src/algorithm-profile-model.js`
- Create: `cloud-mcp/src/algorithm-store.js`
- Modify: `cloud-mcp/src/interview-store.js`
- Modify: `cloud-mcp/src/submit-event.js`
- Create: `cloud-mcp/test/algorithm-profile-model.test.js`
- Create: `cloud-mcp/test/algorithm-store.test.js`
- Modify: `cloud-mcp/test/interview-store.test.js`
- Modify: `cloud-mcp/test/end-to-end.test.js`

- [ ] 为 `rebuildAlgorithmProfile(events, { now })` 写失败测试：只使用已验证的 `algorithm.learning.completed`；中性 `consulted` 不产生弱点；快照包含 `headEventId`、`sourceEventKeys`、`currentTopic`、`topicMastery`、`weaknesses`、`pendingProblemIds`。

- [ ] 为 `createAlgorithmStore` 写失败测试：学习事件成功后创建算法快照；`algorithm.daily-plan-created` 写入 `algorithm/plans/daily/daily-plan-<date>-<planId>.json`；同日同 plan key 幂等复用；投影失败返回 `profile_cache_pending` 且不重复事件。

- [ ] 修改面试快照测试，要求 `interview/profile/snapshots/` 位于同一全局用户根下；会话事件不创建快照，复盘事件创建快照。

- [ ] 实现最小 reducer/store，并将 `submit-event.js` 的算法 handler 从裸 `eventStore.appendEvent` 切换到 `algorithmStore.submitLearning` 或 `algorithmStore.createDailyPlan`。

- [ ] 修改 `interview-store.js` 的 `createSnapshot`，使用 `layout.ensureDomainPath(userId, "interview", ["profile", "snapshots"])`，删除任何根级 `interview/users` 创建逻辑。

- [ ] 运行：

```bash
cd cloud-mcp
node --test test/algorithm-profile-model.test.js test/algorithm-store.test.js test/interview-store.test.js test/end-to-end.test.js
```

Expected: all pass；端到端 fake Drive 中不存在 namespace 级 `users` 或 `user-registry`。

- [ ] Commit:

```bash
git add cloud-mcp/src/algorithm-profile-model.js cloud-mcp/src/algorithm-store.js cloud-mcp/src/interview-store.js cloud-mcp/src/submit-event.js cloud-mcp/test
git commit -m "feat: materialize algorithm and interview data in canonical paths"
```

## Task 5: 规范化 `algorithm-learning`

**Files:**

- Modify: `algorithm-learning/SKILL.md`
- Modify: `algorithm-learning/references/algorithm-profile-contract.md`
- Modify: `algorithm-learning/references/algorithm-daily-protocol.md`
- Modify: `algorithm-learning/references/daily-scheduler-prompt-template.md`
- Modify: `algorithm-learning/references/google-drive-runtime.md`
- Modify: `algorithm-learning/references/2026-08-11-algorithm-profile-system-design.md`
- Modify: `algorithm-learning/references/2026-08-11-algorithm-profile-system-implementation-plan.md`
- Modify: `algorithm-learning/references/2026-08-11-append-only-profile-refactor-plan.md`
- Modify: `algorithm-learning/references/2026-08-11-conversation-identity-gate-plan.md`
- Modify: `algorithm-learning/tests/test_skill_contract.py`
- Modify: `algorithm-learning/tests/test_append_only_profile_model.py`

- [ ] 先把契约测试改成期望：按姓名直接解析/注册、全局 `user-registry`、`users/<userId>/algorithm/...`、每日题单位于 `plans/daily`、所有写入调用 `submit_event`、Worker 物化快照。

- [ ] 增加 forbidden assertions：当前有效文件不得把 `algorithm/users/`、`practice/`、`profile/current` 或 `identity.list/create/verify` 当作当前流程。

- [ ] 运行并确认测试在旧文本上失败：

```bash
python -m unittest discover -s algorithm-learning/tests -v
```

- [ ] 重写 `SKILL.md` 的身份流程：直接提交姓名；Worker 返回已有或新建 `userId`；不再展示 A/B 用户选择。保留原算法答疑、渐进提示、最小修改和事件证据规则。

- [ ] 统一四份当前 reference：

```text
DriveRoot/my-chatGPT-skills/users/<userId>/algorithm/events/
DriveRoot/my-chatGPT-skills/users/<userId>/algorithm/profile/snapshots/
DriveRoot/my-chatGPT-skills/users/<userId>/algorithm/plans/daily/
```

每日模板只调用 `algorithm-learning`/`submit_event`，不得指示任务直接读写 Drive 或 `current snapshot`。

- [ ] 对四份 `2026-08-11-*` 历史设计/计划在标题后增加统一 banner：`Archived / superseded; paths below are historical and MUST NOT be used for writes.` 不改写历史事实，但链接到当前 `algorithm-profile-contract.md`。

- [ ] 运行：

```bash
python -m unittest discover -s algorithm-learning/tests -v
rg -n 'algorithm/users/|profile/current|profile/history|practice/' algorithm-learning \
  -g '!references/2026-08-11-*'
```

Expected: tests pass；`rg` 对当前有效文件无命中。

- [ ] Commit:

```bash
git add algorithm-learning
git commit -m "docs: normalize algorithm learning persistence contract"
```

## Task 6: 规范化模拟面试技能与共享 Schema

**Files:**

- Modify: `conducting-java-backend-mock-interviews/SKILL.md`
- Modify: `conducting-java-backend-mock-interviews/references/candidate-profile-integration.md`
- Modify: `conducting-java-backend-mock-interviews/references/interview-protocol.md`
- Modify: `conducting-java-backend-mock-interviews/schemas/README.md`
- Modify: `conducting-java-backend-mock-interviews/schemas/manifest.json`
- Modify: `conducting-java-backend-mock-interviews/schemas/contracts.schema.json`
- Modify: `conducting-java-backend-mock-interviews/tests/test_cross_skill_contract.py`
- Modify: `conducting-java-backend-mock-interviews/tests/test_mock_handoff.py`

- [ ] 先更新 cross-skill 测试：三个技能都必须提到姓名解析、全局 `userId`、`my-chatGPT-skills` 和 `submit_event`，且不得要求 `identity.list/create/verify`、CandidateIndex 或 `candidate_id`。

- [ ] 运行并确认旧身份门禁文本导致失败：

```bash
python -m unittest discover -s conducting-java-backend-mock-interviews/tests -v
```

- [ ] 重写模拟面试身份段：输入姓名，`submit_event` 返回或创建用户；会话事件落入 `users/<userId>/interview/events/`。保留“一次只问一道”“原回答不可改写”“会话不更新画像”和本地副本规则。

- [ ] 将 `candidate-profile-integration.md` 改写为 `userId` 与领域画像交接契约；移除 CandidateIndex、ConfirmedCandidateContext 和候选人目录。统一 `interview-protocol.md` 的题源比例为当前 `SKILL.md` 的 55/15/10/20，避免已有文档漂移。

- [ ] 更新 manifest，仅列出当前 schema-1.2 定义：`Identity`、`Registration`、`Question`、`SessionEvent`、`QuestionReview`、`ProfileChange`、`ReviewEvent`、`ProfileSnapshot`。保持 conducting/reviewing 两份 schema 字节一致。

- [ ] 确认 `mock_handoff.py` 仍只写 `outputs/interview/<userId>/`，没有任何 Drive 调用；补充测试证明本地路径不会被拼入云端事件路径。

- [ ] 运行：

```bash
python -m unittest discover -s conducting-java-backend-mock-interviews/tests -v
```

- [ ] Commit:

```bash
git add conducting-java-backend-mock-interviews
git commit -m "docs: normalize mock interview identity and storage contracts"
```

## Task 7: 规范化面试复盘并清理活动中的旧候选人模型

**Files:**

- Modify: `reviewing-java-backend-interviews/SKILL.md`
- Modify: `reviewing-java-backend-interviews/references/google-drive-runtime.md`
- Modify: `reviewing-java-backend-interviews/references/profile-contract.md`
- Modify: `reviewing-java-backend-interviews/references/review-protocol.md`
- Modify: `reviewing-java-backend-interviews/references/shared-interview-system-design.md`
- Modify: `reviewing-java-backend-interviews/references/cloud-smoke-test.md`
- Modify: `reviewing-java-backend-interviews/references/2026-08-06-unified-interview-system-implementation-plan.md`
- Modify: `reviewing-java-backend-interviews/schemas/README.md`
- Modify: `reviewing-java-backend-interviews/schemas/manifest.json`
- Modify: `reviewing-java-backend-interviews/schemas/contracts.schema.json`
- Modify: `reviewing-java-backend-interviews/scripts/interview_core.py`
- Modify: `reviewing-java-backend-interviews/scripts/create_review_report.py`
- Modify: `reviewing-java-backend-interviews/tests/test_interview_core.py`
- Modify: `reviewing-java-backend-interviews/tests/test_create_review_report.py`
- Delete: `reviewing-java-backend-interviews/tests/fixtures/cloud_smoke_candidate_index.json`
- Replace: `reviewing-java-backend-interviews/tests/fixtures/cloud_smoke_mock_session.json`

- [ ] 先改测试：所有运行时对象使用 `schemaVersion/userId/username/sessionId/reviewVersion`；测试中不再构造 `candidate_id/profile_version/current_profile`。

- [ ] 运行并确认 legacy validation/reducer 测试失败：

```bash
python -m unittest discover -s reviewing-java-backend-interviews/tests -v
```

- [ ] 保留 `interview_core.py` 的 schema-1.2 `create_review_event`、`save_review_json`、题源/领域纯函数；删除不再被当前 Skill 使用的 schema-1.0 CandidateProfile validator、乐观 current-profile 更新和 `candidate_id` reducer。画像 reducer 的唯一活动实现是 Worker 的 `profile-model.js`。

- [ ] 让 `create_review_report.py` 只以 schema-1.2 review JSON 为输入；报告身份使用 `username/userId`。若需要保留旧报告读取，单独放入明确命名的只读 legacy adapter，不能出现在当前保存路径。

- [ ] 重写六份当前 reference：会话/复盘事件位于 `users/<userId>/interview/events/`，快照位于 `users/<userId>/interview/profile/snapshots/`，报告只在本地输出。删除当前流程中的 `system/candidate_index.json`、`candidates/<candidate_id>/`、`profile/current_profile.json`、原始 transcript 和 DOCX 云端上传。

- [ ] 在历史实现计划标题后加入 archived/superseded banner；删除旧 CandidateIndex fixture，替换为 schema-1.2 session fixture。

- [ ] 同步 reviewing schema/manifest 后再次执行 byte-identical 测试。

- [ ] 运行：

```bash
python -m unittest discover -s reviewing-java-backend-interviews/tests -v
python -m unittest discover -s conducting-java-backend-mock-interviews/tests -v
rg -n 'system/candidate_index|candidates/<candidate_id>|profile/current_profile|candidate_id' \
  reviewing-java-backend-interviews \
  -g '!references/2026-08-06-unified-interview-system-implementation-plan.md'
```

Expected: tests pass；当前活动文件无旧候选人契约命中。

- [ ] Commit:

```bash
git add -A reviewing-java-backend-interviews conducting-java-backend-mock-interviews/schemas
git commit -m "refactor: normalize interview review identity and profile contracts"
```

## Task 8: 实现简历知识域的证据、评分和选题 reducer

**Files:**

- Create: `cloud-mcp/src/resume-knowledge-model.js`
- Create: `cloud-mcp/src/daily-plan-selector.js`
- Modify: `cloud-mcp/src/protocol.js`
- Create: `cloud-mcp/test/resume-knowledge-model.test.js`
- Create: `cloud-mcp/test/daily-plan-selector.test.js`

- [ ] 为证据规则写测试：`explicit` 可直接出题，`strong-inference` 必须条件式或已确认，`unsupported/rejected` 禁止进入题库；无有效 resume snapshot 时返回 `resume_required`。

- [ ] 为掌握度写测试：首次分数直接成为 mastery；不同日期使用 `0.6 * score + 0.4 * old`；未考题不计知识点平均分但计入 coverage denominator。

```js
assert.equal(updateMastery(undefined, 70), 70);
assert.equal(updateMastery(50, 80), 68);
assert.deepEqual(knowledgePointStats([{ status: "tested", mastery: 80 }, { status: "untested" }]), {
  mastery: 80, tested: 1, total: 2, coverage: 0.5
});
```

- [ ] 为当日首答写测试：`userId + localDate + questionKey` 相同只接受最早有效 `answer-scored`；同题次日允许再次参与 reducer。

- [ ] 为每日五题选择写测试：两道最低分、一题未考简历明示、一题项目场景、一题历史低分复测；语义 `questionKey` 去重；不足五题时返回更少且不补无依据通用题；已存在当日 plan 时原样复用。

- [ ] 运行并确认模块不存在：

```bash
cd cloud-mcp
node --test test/resume-knowledge-model.test.js test/daily-plan-selector.test.js
```

- [ ] 实现纯函数：

```js
normalizeQuestionBank({ resumeSnapshot, claims, questions })
rebuildResumeKnowledgeProfile(events, questionBank, { now })
firstScorePerDay(events)
updateMastery(previous, score)
selectDailyQuestions({ questionBank, profile, localDate, limit: 5 })
```

- [ ] 在 `protocol.js` 为六种 resume-knowledge 事件写精确字段白名单和类型验证。`answer-scored` 的四维分数必须分别在范围内且加总为总分；`questionKey/localDate/resumeVersion` 必填。

- [ ] 运行：

```bash
cd cloud-mcp
node --test test/resume-knowledge-model.test.js test/daily-plan-selector.test.js test/mcp.test.js
```

- [ ] Commit:

```bash
git add cloud-mcp/src/resume-knowledge-model.js cloud-mcp/src/daily-plan-selector.js cloud-mcp/src/protocol.js cloud-mcp/test
git commit -m "feat: add resume knowledge scoring and daily selection models"
```

## Task 9: 物化简历、题库、题单和人物快照

**Files:**

- Create: `cloud-mcp/src/resume-knowledge-store.js`
- Modify: `cloud-mcp/src/submit-event.js`
- Modify: `cloud-mcp/src/google-drive.js`
- Create: `cloud-mcp/test/resume-knowledge-store.test.js`
- Modify: `cloud-mcp/test/end-to-end.test.js`

- [ ] 编写 store 测试，锁定物化路径：

```text
users/<userId>/resume-knowledge/sources/resume/snapshots/resume-<version>-<fingerprint>.json
users/<userId>/resume-knowledge/question-bank/snapshots/question-bank-<version>-<eventId>.json
users/<userId>/resume-knowledge/events/event-<eventId>.json
users/<userId>/resume-knowledge/profile/snapshots/snapshot-<UTC>-<headEventId>.json
users/<userId>/resume-knowledge/plans/daily/daily-plan-<localDate>-<planId>.json
```

- [ ] 增加行为测试：同日重复 `answer-scored` 返回 `already_scored_today` 且不创建第二事件/快照；次日创建；原事件已存在而快照缺失时，同幂等键重试只补投影。

- [ ] 运行并确认失败：

```bash
cd cloud-mcp
node --test test/resume-knowledge-store.test.js
```

- [ ] 实现 `createResumeKnowledgeStore({ eventStore, layout, drive, now })`，提供：

```js
ingestResume(identity, event)
recordClaimDecision(identity, event)
saveQuestionBank(identity, event)
getOrCreateDailyPlan(identity, event)
scoreAnswer(identity, event)
```

所有写入执行创建 → 读回 → 父目录/内容校验。`scoreAnswer` 先检查日期级幂等，再追加事件、rebuild profile、创建不可变快照。

- [ ] 将六种 resume-knowledge handler 接入 `submit-event.js`，统一返回 `status`、`identity`、事件 receipt 与 projection receipt。禁止 handler 直接拼 Drive 路径。

- [ ] 扩展端到端测试：新用户简历 → 题库 → 当日题单 → 首答评分 → 同日重答 → 次日重答；验证路径和 mastery 数值。

- [ ] 运行：

```bash
cd cloud-mcp
npm test
```

Expected: all Node tests pass。

- [ ] Commit:

```bash
git add cloud-mcp/src/resume-knowledge-store.js cloud-mcp/src/submit-event.js cloud-mcp/src/google-drive.js cloud-mcp/test
git commit -m "feat: persist resume knowledge events and projections"
```

## Task 10: 创建 `java-knowledge-based-on-resume-learn-skill`

**Files:**

- Create: `java-knowledge-based-on-resume-learn-skill/SKILL.md`
- Create: `java-knowledge-based-on-resume-learn-skill/agents/openai.yaml`
- Create: `java-knowledge-based-on-resume-learn-skill/references/resume-evidence-policy.md`
- Create: `java-knowledge-based-on-resume-learn-skill/references/question-bank-contract.md`
- Create: `java-knowledge-based-on-resume-learn-skill/references/feedback-scoring-contract.md`
- Create: `java-knowledge-based-on-resume-learn-skill/references/profile-storage-contract.md`
- Create: `java-knowledge-based-on-resume-learn-skill/references/daily-task-prompt-template.md`
- Create: `java-knowledge-based-on-resume-learn-skill/tests/test_skill_contract.py`

- [ ] 先写文本契约测试，要求 Skill 明确包含：三级证据、无简历停止、Java/MySQL/Redis/MQ/中间件覆盖、每题反馈六部分、40/25/20/15 评分、回答链、0.6/0.4 mastery、同日首答、低分优先、五题槽位、`submit_event` 唯一写入和规范目录。

- [ ] 增加 forbidden assertions：不得声称强推断是项目事实；不得在用户作答前展示评分点/参考答案；不得直接使用 Google Drive 写工具；不得创建定时任务。

- [ ] 运行并确认技能尚不存在：

```bash
python -m unittest discover -s java-knowledge-based-on-resume-learn-skill/tests -v
```

- [ ] 编写 `SKILL.md` 四种模式：简历初始化/更新、逐题学习、每日练习、掌握度查看。每次先按姓名解析用户；缺失时注册；无简历时停止；持久化只调用 `submit_event`。

- [ ] 将详细规则拆入五份 references。每日模板只描述用户自行建立的 09:00 `Asia/Shanghai` 调用示例，不创建 automation；当天 plan 已存在时原样返回。

- [ ] `agents/openai.yaml` 的名称和描述应强调“严格依据简历、逐题反馈、弱项复测”，避免触发到完整模拟面试或真实面试复盘。

- [ ] 运行：

```bash
python -m unittest discover -s java-knowledge-based-on-resume-learn-skill/tests -v
python /root/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  java-knowledge-based-on-resume-learn-skill
```

Expected: contract tests and validator pass。

- [ ] Commit:

```bash
git add java-knowledge-based-on-resume-learn-skill
git commit -m "feat: add resume driven Java knowledge learning skill"
```

## Task 11: 实现非破坏性旧数据迁移事件

**Files:**

- Create: `cloud-mcp/src/migration-store.js`
- Modify: `cloud-mcp/src/legacy-reader.js`
- Modify: `cloud-mcp/src/submit-event.js`
- Create: `cloud-mcp/test/migration-store.test.js`
- Modify: `cloud-mcp/test/end-to-end.test.js`

- [ ] 编写 dry-run 测试：按标准化姓名关联旧 algorithm/interview 注册；输出 source/target、内容哈希、冲突和跳过项；不得调用 `createJson`。

- [ ] 编写 execute 测试：只复制不存在且哈希匹配的对象；相同内容跳过；同目标键不同内容停止；源对象不 update/move/delete；迁移 receipt 可审计。

- [ ] 运行并确认模块不存在：

```bash
cd cloud-mcp
node --test test/migration-store.test.js
```

- [ ] 实现 `createMigrationStore({ legacyReader, layout, drive, userStore })`：

```js
migrationStore.plan({ displayName, domains })
migrationStore.execute({ migrationId, approvedPlanHash })
```

`system.legacy-migration-requested` payload 必须显式包含 `mode: "dry-run" | "execute"`；execute 必须携带前次 plan hash，防止扫描结果变化后盲目复制。

- [ ] 迁移后读取仍遵循规范路径优先。不得自动执行真实 Drive 迁移；这里只交付能力和测试，实际运行必须由用户另行触发。

- [ ] 运行：

```bash
cd cloud-mcp
node --test test/legacy-reader.test.js test/migration-store.test.js test/end-to-end.test.js
```

- [ ] Commit:

```bash
git add cloud-mcp/src/migration-store.js cloud-mcp/src/legacy-reader.js cloud-mcp/src/submit-event.js cloud-mcp/test
git commit -m "feat: add auditable non-destructive legacy migration"
```

## Task 12: 全仓契约、文档和最终验证

**Files:**

- Modify: `AGENTS.md`
- Modify: `cloud-mcp/README.md`
- Modify: `cloud-mcp/test/local-mcp-bridge.test.mjs`
- Create: `tests/test_repository_storage_contract.py`
- Modify if needed: `docs/superpowers/specs/2026-08-29-java-resume-knowledge-design.md`

- [ ] 编写仓库级扫描测试。当前活动文件出现以下字符串时失败：

```text
algorithm/users/
interview/users/
profile/current
profile/history
system/candidate_index.json
candidates/<candidate_id>/
identity.list
identity.create
identity.verify
```

允许列表只能包含：`cloud-mcp/src/legacy-reader.js`、`cloud-mcp/src/migration-store.js`、对应测试、`docs/superpowers/` 历史文档，以及已带 archived/superseded banner 的历史 reference。

- [ ] 运行并确认 `AGENTS.md`、README 等旧说明使测试失败：

```bash
python -m unittest tests/test_repository_storage_contract.py -v
```

- [ ] 更新 `AGENTS.md` 路由，加入新技能，并把身份规则改为“按姓名全局解析/缺失注册”。更新 `cloud-mcp/README.md` 的 envelope 示例、规范目录、错误状态、部署配置和迁移安全边界。

- [ ] 保持 local bridge 只暴露 `submit_event`，更新测试示例事件为 `system.user-registered` 或规范业务事件。

- [ ] 执行全部自动化测试：

```bash
cd cloud-mcp && npm test
cd ..
python -m unittest discover -s algorithm-learning/tests -v
python -m unittest discover -s conducting-java-backend-mock-interviews/tests -v
python -m unittest discover -s reviewing-java-backend-interviews/tests -v
python -m unittest discover -s java-knowledge-based-on-resume-learn-skill/tests -v
python -m unittest tests/test_repository_storage_contract.py -v
```

- [ ] 验证全部技能：

```bash
for skill in \
  algorithm-learning \
  conducting-java-backend-mock-interviews \
  reviewing-java-backend-interviews \
  java-knowledge-based-on-resume-learn-skill
do
  python /root/.codex/skills/.system/skill-creator/scripts/quick_validate.py "$skill"
done
```

- [ ] 最终只读审计：

```bash
rg -n 'algorithm/users/|interview/users/|profile/current|profile/history|system/candidate_index|candidates/<candidate_id>|identity\.(list|create|verify)' \
  AGENTS.md algorithm-learning conducting-java-backend-mock-interviews \
  reviewing-java-backend-interviews java-knowledge-based-on-resume-learn-skill cloud-mcp \
  -g '!cloud-mcp/src/legacy-reader.js' \
  -g '!cloud-mcp/src/migration-store.js' \
  -g '!cloud-mcp/test/*legacy*' \
  -g '!cloud-mcp/test/migration-store.test.js' \
  -g '!**/references/2026-*'
```

Expected: no matches。

- [ ] 确认未执行任何真实 Drive 写入或迁移，然后提交：

```bash
git add AGENTS.md cloud-mcp/README.md cloud-mcp/test/local-mcp-bridge.test.mjs tests docs/superpowers/specs
git commit -m "docs: finalize unified skill storage contract"
```

## Completion Checklist

- [ ] `git status --short` 只包含预期文件或为空。
- [ ] `git log --oneline --decorate -12` 显示每个任务的独立提交。
- [ ] 全部 Node、Python、cross-skill、repository scan 和 `quick_validate.py` 测试通过。
- [ ] fake Drive 端到端路径全部位于 `root/my-chatGPT-skills/users/<userId>/...`。
- [ ] 同名跨领域得到同一 `userId`；缺失姓名注册；不同姓名隔离；冲突停止。
- [ ] 算法事件生成算法快照；模拟会话不生成画像；复盘生成面试快照；简历首答生成掌握度快照。
- [ ] 同题同日重复回答只反馈不落第二事件；次日允许再次更新。
- [ ] 每日选题严格证据约束并按低分优先，证据不足时少于五题。
- [ ] 所有技能写入都经 `submit_event`，没有直接 Drive 写入指令。
- [ ] 迁移仅提供 dry-run/显式 execute 能力，旧对象未被移动、覆盖或删除。
