import assert from "node:assert/strict";
import test from "node:test";
import { canonicalHash, createEventStore } from "../src/event-store.js";

const identity = { userId: "00000000-0000-4000-8000-000000000001", username: "Ada" };
const event = {
  schemaVersion: "1.2",
  eventId: "10000000-0000-4000-8000-000000000001",
  eventKey: "session-MOCK-1-completed",
  eventType: "interview.session.completed",
  userId: identity.userId,
  username: identity.username,
  sessionId: "MOCK-1",
  interviewType: "mock",
  domain: "algorithms",
  completedAt: "2026-08-14T10:00:00.000Z"
};

function fakeDrive() {
  const folders = new Map([["users", { id: "users", name: "users", parents: ["root"] }]]);
  const files = new Map();
  const createdJsonFiles = [];
  let listings = [];
  let number = 0;
  const childFolders = (parentId, name) => [...folders.values()].filter((folder) => folder.parents[0] === parentId && (!name || folder.name === name));
  return {
    rootFolderId: "root",
    createdJsonFiles,
    async findFolder(parentId, name) { return childFolders(parentId, name)[0] ?? null; },
    async ensureFolder(parentId, name) {
      const found = childFolders(parentId, name)[0];
      if (found) return found;
      const folder = { id: `folder-${++number}`, name, parents: [parentId] };
      folders.set(folder.id, folder);
      return folder;
    },
    async listChildren(parentId, { name, foldersOnly } = {}) {
      const children = foldersOnly ? [...folders.values()] : [...folders.values(), ...files.values()];
      return children.filter((item) => item.parents[0] === parentId && (!name || item.name === name));
    },
    setJsonListings(value) { listings = value; },
    async listJson(parentId) {
      const listing = listings.shift();
      return listing ? listing.map((id) => structuredClone(files.get(id))) : [...files.values()].filter((file) => file.parents[0] === parentId);
    },
    async createJson(parentId, name, value) {
      const file = { id: `file-${++number}`, name, parents: [parentId], mimeType: "application/json", value: structuredClone(value) };
      files.set(file.id, file);
      createdJsonFiles.push(file);
      return structuredClone(file);
    },
    async readJson(id) { return structuredClone(files.get(id)); }
  };
}

function setup() {
  const drive = fakeDrive();
  const namespaceStore = { verifyIdentity: async (value) => ({ status: "ok", identity: structuredClone(value) }) };
  return { drive, store: createEventStore({ namespaceStore, drive }) };
}

test("same event key and content reuses the earliest verified event", async () => {
  const { drive, store } = setup();
  const first = await store.appendEvent(identity, event);
  const second = await store.appendEvent(identity, structuredClone(event));
  assert.equal(second.receipt.fileId, first.receipt.fileId);
  assert.equal(drive.createdJsonFiles.length, 1);
});

test("same event key with different content is rejected", async () => {
  const { store } = setup();
  await store.appendEvent(identity, event);
  await assert.rejects(() => store.appendEvent(identity, { ...event, domain: "distributed-systems" }), /event_key_conflict/);
});

test("append stores a verified hash under an event-id filename", async () => {
  const { drive, store } = setup();
  const result = await store.appendEvent(identity, event);
  assert.equal(drive.createdJsonFiles[0].name, `event-${event.eventId}.json`);
  assert.match(result.event.contentHash, /^[0-9a-f]{64}$/);
});

test("canonical hash treats event fields named like Drive metadata as content", async () => {
  assert.notEqual(await canonicalHash(event), await canonicalHash({ ...event, name: "user-supplied-name" }));
});

test("duplicate retry returns the previously verified file instead of another same-name file", async () => {
  const { drive, store } = setup();
  const first = await store.appendEvent(identity, event);
  const duplicate = await drive.createJson(drive.createdJsonFiles[0].parents[0], `event-${event.eventId}.json`, first.event);
  drive.setJsonListings([[first.receipt.fileId, duplicate.id], [duplicate.id, first.receipt.fileId]]);
  const retried = await store.appendEvent(identity, structuredClone(event));
  assert.equal(retried.receipt.fileId, first.receipt.fileId);
});
