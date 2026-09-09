import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));

test("T08 approved inventory is explicit and contains the account gateway plus four profile skills", async () => {
  const inventoryPath = join(root, "docs", "releases", "device-plugin-inventory.md");
  assert.equal(existsSync(inventoryPath), true);
  const inventory = await readFile(inventoryPath, "utf8");
  for (const name of ["account-gateway", "algorithm-learning", "backend-project-learning", "conducting-java-backend-mock-interviews", "reviewing-java-backend-interviews", "java-knowledge-based-on-resume-learn-skill", "software-project-learning", "review-model-routing"]) {
    assert.match(inventory, new RegExp(`^\\| ${name} \\|`, "m"));
  }
  assert.match(inventory, /sourceSha|source SHA/i);
  assert.match(inventory, /packageHash/i);
});

test("T08 account gateway skill has no domain reducer or profile schema dependency", async () => {
  const skill = await readFile(join(root, "account-gateway", "SKILL.md"), "utf8");
  assert.match(skill, /submit_event/);
  assert.match(skill, /account\.(current|register|bind|switch|unbind)/);
  assert.doesNotMatch(skill, /reducer|algorithm\.learning|interview\.session|resume-knowledge\.answer-scored/);
});

test("T08 build script emits a deterministic manifest without credentials or absolute user paths", async () => {
  const script = await readFile(join(root, "scripts", "build-device-plugin.mjs"), "utf8");
  assert.match(script, /packageHash/);
  assert.match(script, /submit_event/);
  assert.doesNotMatch(script, /LOCALAPPDATA|credential|secret/i);
  assert.doesNotMatch(script, /C:\\\\Users\\\\/i);
});

test("T10 release candidate keeps registration and admin initialization disabled by default", async () => {
  const script = await readFile(join(root, "scripts", "build-device-plugin.mjs"), "utf8");
  const runbook = await readFile(join(root, "docs", "releases", "device-release.md"), "utf8");
  assert.match(script, /selfRegister:\s*false/);
  assert.match(script, /adminInit:\s*false/);
  assert.match(runbook, /默认.*关闭|false/i);
  assert.match(runbook, /备份|回退/);
});
