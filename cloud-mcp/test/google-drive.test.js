import assert from "node:assert/strict";
import test from "node:test";
import { findOrCreateCandidateFolder, formatGoogleDriveWriteError, listCandidates, uploadDriveFile } from "../src/google-drive.js";

const env = { GOOGLE_DRIVE_FOLDER_ID: "root" };

test("formatGoogleDriveWriteError preserves Drive status and message", () => {
  assert.equal(
    formatGoogleDriveWriteError(403, { error: { message: "The caller does not have permission" } }),
    "Google Drive write failed (403): The caller does not have permission"
  );
});

test("findOrCreateCandidateFolder reuses the earliest exact-name folder", async () => {
  const result = await findOrCreateCandidateFolder(env, { displayName: "小明" }, {
    findFoldersByName: async () => [
      { id: "newer", name: "小明", createdTime: "2026-08-13T00:00:00.000Z" },
      { id: "older", name: "小明", createdTime: "2026-01-01T00:00:00.000Z" }
    ],
    createFolder: async () => { throw new Error("must not create"); }
  });
  assert.deepEqual(result, { displayName: "小明", folderId: "older", created: false });
});

test("findOrCreateCandidateFolder creates a name folder and identity when absent", async () => {
  const calls = [];
  const result = await findOrCreateCandidateFolder(env, { displayName: "小明" }, {
    now: () => "2026-08-13T00:00:00.000Z",
    findFoldersByName: async () => [],
    createFolder: async (...args) => { calls.push(args); return { id: "folder-1" }; },
    uploadFile: async (...args) => { calls.push(args); return { id: "identity-1" }; }
  });
  assert.deepEqual(result, { displayName: "小明", folderId: "folder-1", created: true });
  assert.deepEqual(calls[0], ["root", "小明"]);
  assert.equal(calls[1][1], "identity.json");
  assert.match(calls[1][2], /小明/);
});

test("findOrCreateCandidateFolder stops when the identity write fails", async () => {
  await assert.rejects(() => findOrCreateCandidateFolder(env, { displayName: "小明" }, {
    findFoldersByName: async () => [],
    createFolder: async () => ({ id: "folder-1" }),
    uploadFile: async () => { throw new Error("Drive unavailable"); }
  }), /Drive unavailable/);
});

test("uploadDriveFile rejects a Drive response without a file id", async () => {
  await assert.rejects(() => uploadDriveFile(env, "folder-1", "session.json", "{}", "application/json", {
    uploadFile: async () => ({})
  }), /file id/);
});

test("listCandidates returns direct name-folder summaries", async () => {
  const result = await listCandidates(env, { query: "小" }, {
    listFolders: async () => [{ id: "folder-1", name: "小明", createdTime: "2026-01-01T00:00:00.000Z" }]
  });
  assert.deepEqual(result, [{ displayName: "小明", folderId: "folder-1" }]);
});
