import assert from "node:assert/strict";
import test from "node:test";
import { createCandidate } from "../src/candidates.js";

function db() {
  const rows = [];
  return {
    prepare() {
      return {
        bind(...values) {
          return {
            async run() {
              rows.push(values);
              return { success: true };
            }
          };
        }
      };
    },
    rows
  };
}

test("createCandidate creates a unique candidate summary", async () => {
  const result = await createCandidate(db(), { displayName: "小明" }, "2026-08-13T00:00:00.000Z", () => "abc");
  assert.deepEqual(result, {
    schemaVersion: "1.0",
    candidateId: "CAND-abc",
    displayName: "小明",
    distinguishingNote: "",
    createdAt: "2026-08-13T00:00:00.000Z"
  });
});

test("createCandidate rejects a blank display name", async () => {
  await assert.rejects(
    () => createCandidate(db(), { displayName: "  " }, "2026-08-13T00:00:00.000Z", () => "abc"),
    { code: "invalid_argument" }
  );
});
