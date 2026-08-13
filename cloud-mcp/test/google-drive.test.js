import assert from "node:assert/strict";
import test from "node:test";
import { createCandidateFolder, uploadDriveFile } from "../src/google-drive.js";

const env = { GOOGLE_DRIVE_FOLDER_ID: "root" };

test("createCandidateFolder returns only after Drive creates its folder and metadata", async () => {
  const calls = [];
  const candidate = await createCandidateFolder(env, { displayName: "小明" }, {
    uuid: () => "abc",
    now: () => "2026-08-13T00:00:00.000Z",
    createFolder: async (...args) => { calls.push(args); return { id: "folder-1" }; },
    uploadFile: async (...args) => { calls.push(args); return { id: "metadata-1" }; }
  });
  assert.equal(candidate.candidateId, "CAND-abc");
  assert.equal(candidate.folderId, "folder-1");
  assert.equal(calls.length, 2);
});

test("createCandidateFolder stops when Drive metadata creation fails", async () => {
  await assert.rejects(() => createCandidateFolder(env, { displayName: "小明" }, {
    uuid: () => "abc",
    now: () => "2026-08-13T00:00:00.000Z",
    createFolder: async () => ({ id: "folder-1" }),
    uploadFile: async () => { throw new Error("Drive unavailable"); }
  }), /Drive unavailable/);
});

test("uploadDriveFile rejects a Drive response without a file id", async () => {
  await assert.rejects(() => uploadDriveFile(env, "folder-1", "session.json", "{}", "application/json", {
    uploadFile: async () => ({})
  }), /file id/);
});

test("listCandidates reads candidate summaries from direct Drive folders", async () => {
  const { listCandidates } = await import("../src/google-drive.js");
  const result = await listCandidates(env, { query: "小" }, {
    listFolders: async () => [{ id: "folder-1", name: "CAND-abc" }],
    readCandidate: async () => ({ candidateId: "CAND-abc", displayName: "小明", folderId: "folder-1" })
  });
  assert.deepEqual(result, [{ candidateId: "CAND-abc", displayName: "小明", folderId: "folder-1" }]);
});
