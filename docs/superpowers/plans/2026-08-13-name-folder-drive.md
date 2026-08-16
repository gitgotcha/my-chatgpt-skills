# 姓名目录直连 Drive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让云端 MCP 只以姓名定位 Google Drive 根目录下的用户文件夹。

**Architecture:** Drive 根目录是唯一数据源。`find_or_create_candidate` 精确查找同名文件夹，缺失时创建文件夹和最小 `identity.json`；其余工具在读写前使用姓名解析该目录。所有操作等待 Drive 返回 ID 后才返回成功。

**Tech Stack:** Cloudflare Workers、原生 JavaScript、Google Drive API、Node.js test。

## Global Constraints

- 不使用候选人 ID、注册表、数据库、队列或异步同步。
- 同名视为同一用户；多个旧同名文件夹时选择最早创建的一项。
- 每一次成功创建或写入均以 Google Drive 返回文件/目录 ID 为准。

---

### Task 1: 姓名目录解析

**Files:**
- Modify: `cloud-mcp/test/google-drive.test.js`
- Modify: `cloud-mcp/src/google-drive.js`

**Interfaces:**
- Produces: `findOrCreateCandidateFolder(env, { displayName }, deps)`，返回 `{ displayName, folderId, created }`。

- [x] **Step 1: 写失败测试**

```js
const result = await findOrCreateCandidateFolder(env, { displayName: "小明" }, {
  findFoldersByName: async () => [{ id: "folder-1", createdTime: "2026-01-01T00:00:00Z" }]
});
assert.deepEqual(result, { displayName: "小明", folderId: "folder-1", created: false });
```

- [x] **Step 2: 运行测试，确认因函数尚不存在而失败**

Run: `node --test test/google-drive.test.js`

- [x] **Step 3: 实现最小目录查询与创建逻辑**

```js
export async function findOrCreateCandidateFolder(env, input, deps = {}) {
  const displayName = input?.displayName?.trim();
  if (!displayName) throw new Error("displayName is required");
  const matches = await findFoldersByName(displayName);
  if (matches[0]) return { displayName, folderId: matches[0].id, created: false };
  const folder = await createFolder(env.GOOGLE_DRIVE_FOLDER_ID, displayName);
  await uploadDriveFile(env, folder.id, "identity.json", JSON.stringify({ displayName }), "application/json", deps);
  return { displayName, folderId: folder.id, created: true };
}
```

- [x] **Step 4: 运行整个测试集，确认通过**

Run: `node --test`

### Task 2: MCP 与技能改为姓名入口

**Files:**
- Modify: `cloud-mcp/test/mcp.test.js`
- Modify: `cloud-mcp/src/index.js`
- Modify: `cloud-mcp/README.md`
- Modify: `algorithm-learning/SKILL.md`
- Modify: `backend-project-learning/SKILL.md`
- Modify: `conducting-java-backend-mock-interviews/SKILL.md`
- Modify: `reviewing-java-backend-interviews/SKILL.md`

**Interfaces:**
- Consumes: `findOrCreateCandidateFolder`。
- Produces: `find_or_create_candidate`、`get_candidate_context`、`submit_artifact` 和 `submit_event` 的 `displayName` 输入。

- [x] **Step 1: 写失败 MCP 测试**

```js
const response = await handleRequest(request("submit_event", { displayName: "小明", event }), env, deps);
assert.equal(uploadedParentId, "folder-1");
```

- [x] **Step 2: 运行测试，确认现有接口拒绝仅提供姓名的调用**

Run: `node --test test/mcp.test.js`

- [x] **Step 3: 最小化改造 MCP 和说明**

```js
const candidate = await drive.findOrCreateCandidateFolder(env, args, deps);
const file = await drive.uploadDriveFile(env, candidate.folderId, fileName, content, contentType, deps);
```

所有技能改为“先用 `displayName` 定位或创建同名 Drive 文件夹，再读写其文件”。

- [x] **Step 4: 运行全套测试与文本检查**

Run: `node --test && git diff --check`

### Task 3: 提交

**Files:**
- Modify: `docs/superpowers/specs/2026-08-13-name-folder-drive-design.md`
- Create: `docs/superpowers/plans/2026-08-13-name-folder-drive.md`
- Modify: Task 1 与 Task 2 的全部文件

- [x] **Step 1: 检查工作区、测试和远端分支**

Run: `node --test && git diff --check && git status --short`

- [x] **Step 2: 提交并推送当前分支**

```bash
git add cloud-mcp algorithm-learning/SKILL.md backend-project-learning/SKILL.md conducting-java-backend-mock-interviews/SKILL.md reviewing-java-backend-interviews/SKILL.md docs/superpowers
git commit -m "refactor: use name folders for Drive users"
git push origin cloud-candidate-mcp
```
