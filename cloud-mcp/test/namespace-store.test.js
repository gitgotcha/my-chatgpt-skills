import assert from "node:assert/strict";
import test from "node:test";
import { createNamespaceStore } from "../src/namespace-store.js";
import { dispatchSubmitEvent } from "../src/submit-event.js";

const USER_ID = "11111111-1111-4111-8111-111111111111";

function fakeDrive(operations, { registrations = [], wrongIdentityParent = false } = {}) {
  const folders = new Map([["root", []]]);
  const files = new Map();
  let nextId = 1;
  const addFolder = (parentId, name) => {
    const folder = { id: `folder-${nextId++}`, name, mimeType: "application/vnd.google-apps.folder", parents: [parentId] };
    folders.set(folder.id, []);
    folders.get(parentId).push(folder);
    return folder;
  };
  const addFile = (parentId, name, value) => {
    const file = { id: `file-${nextId++}`, name, mimeType: "application/json", parents: [parentId] };
    files.set(file.id, { ...file, value });
    folders.get(parentId).push(file);
    return file;
  };
  const namespace = addFolder("root", "interview");
  const registry = addFolder(namespace.id, "user-registry");
  const users = addFolder(namespace.id, "users");
  for (const registration of registrations) addFile(registry.id, `registration-${registration.userId}.json`, registration);

  return {
    rootFolderId: "root",
    async listChildren(parentId) { return [...(folders.get(parentId) ?? [])]; },
    async findFolder(parentId, name) { return (folders.get(parentId) ?? []).find((item) => item.name === name && item.mimeType.includes("folder")) ?? null; },
    async ensureFolder(parentId, name) {
      const existing = await this.findFolder(parentId, name);
      if (existing) return existing;
      operations.push({ type: "folder", parentId, name });
      return addFolder(parentId, name);
    },
    async listJson(parentId) { return (folders.get(parentId) ?? []).filter((item) => item.mimeType === "application/json"); },
    async createJson(parentId, name, value) {
      operations.push({ type: "json", parentId, name, value });
      const file = addFile(parentId, name, value);
      return this.readJson(file.id);
    },
    async readJson(fileId) {
      const file = files.get(fileId);
      return wrongIdentityParent && file.name === "identity.json" ? { ...file, parents: ["wrong-parent"] } : file;
    },
    _folders: folders,
    _addFile: addFile,
    _users: users
  };
}

function fakeDriveWithWrongIdentityParent() {
  const operations = [];
  const drive = fakeDrive(operations, { wrongIdentityParent: true });
  const user = { id: "folder-user", name: USER_ID, mimeType: "application/vnd.google-apps.folder", parents: [drive._users.id] };
  drive._folders.set(user.id, []);
  drive._folders.get(drive._users.id).push(user);
  drive._addFile(user.id, "identity.json", { schemaVersion: "1.2", userId: USER_ID, username: "乔炳源" });
  return drive;
}

function fakeDriveWithDuplicateRegistrations() {
  return fakeDrive([], { registrations: [
    { schemaVersion: "1.2", status: "active", userId: USER_ID, username: "乔炳源", createdAt: "2026-08-14T00:00:00.000Z" },
    { schemaVersion: "1.2", status: "active", userId: "22222222-2222-4222-8222-222222222222", username: "乔炳源", createdAt: "2026-08-14T00:01:00.000Z" }
  ] });
}

test("identity creation writes registration last and returns a verified binding", async () => {
  const operations = [];
  const store = createNamespaceStore({
    namespace: "interview",
    drive: fakeDrive(operations),
    now: () => "2026-08-14T00:00:00.000Z",
    uuid: () => USER_ID
  });
  const result = await store.createIdentity({ username: " 乔炳源 " });
  assert.equal(result.status, "ok");
  assert.deepEqual(result.identity, { userId: USER_ID, username: "乔炳源", verified: true });
  assert.equal(operations.at(-1).name, `registration-${USER_ID}.json`);
});

test("identity verification rejects a wrong parent", async () => {
  const store = createNamespaceStore({ namespace: "interview", drive: fakeDriveWithWrongIdentityParent() });
  await assert.rejects(() => store.verifyIdentity({ userId: USER_ID, username: "乔炳源" }), /identity_mismatch/);
});

test("duplicate active usernames return username_conflict", async () => {
  const store = createNamespaceStore({ namespace: "interview", drive: fakeDriveWithDuplicateRegistrations() });
  await assert.rejects(() => store.createIdentity({ username: "乔炳源" }), /username_conflict/);
});

test("identity listing ignores malformed registrations and sorts accepted records", async () => {
  const drive = fakeDrive([], { registrations: [
    { schemaVersion: "1.2", status: "active", userId: "22222222-2222-4222-8222-222222222222", username: "B", createdAt: "2026-08-14T00:01:00.000Z" },
    { schemaVersion: "1.1", status: "active", userId: USER_ID, username: "ignored", createdAt: "2026-08-14T00:00:00.000Z" },
    { schemaVersion: "1.2", status: "active", userId: USER_ID, username: "A", createdAt: "2026-08-14T00:00:00.000Z" }
  ] });
  const result = await createNamespaceStore({ namespace: "interview", drive }).listIdentities();
  assert.deepEqual(result, { status: "ok", data: { registrations: [
    { schemaVersion: "1.2", status: "active", userId: USER_ID, username: "A", createdAt: "2026-08-14T00:00:00.000Z" },
    { schemaVersion: "1.2", status: "active", userId: "22222222-2222-4222-8222-222222222222", username: "B", createdAt: "2026-08-14T00:01:00.000Z" }
  ] } });
});

test("identity listing returns an empty registry for a missing namespace root", async () => {
  const drive = fakeDrive([]);
  const result = await createNamespaceStore({ namespace: "algorithm", drive }).listIdentities();
  assert.deepEqual(result, { status: "ok", data: { registrations: [] } });
});

test("only algorithm and interview are valid namespaces", () => {
  assert.throws(() => createNamespaceStore({ namespace: "other", drive: fakeDrive([]) }), /invalid_namespace/);
});

test("submit_event routes identity.list through the namespace store", async () => {
  const result = await dispatchSubmitEvent({}, {
    schemaVersion: "1.2",
    namespace: "interview",
    eventType: "identity.list",
    payload: {},
    requestId: USER_ID
  }, { drive: fakeDrive([]) });
  assert.deepEqual(result, { status: "ok", data: { registrations: [] } });
});
