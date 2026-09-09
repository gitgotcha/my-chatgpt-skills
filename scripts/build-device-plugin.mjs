import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const run = promisify(execFile);
const root = new URL("..", import.meta.url).pathname.replace(/^\/+/, "").replaceAll("/", "\\");
const names = Object.freeze([
  "account-gateway", "algorithm-learning", "backend-project-learning",
  "conducting-java-backend-mock-interviews", "reviewing-java-backend-interviews",
  "java-knowledge-based-on-resume-learn-skill", "software-project-learning"
]);

function sha(value) { return createHash("sha256").update(value).digest("hex"); }
function canonical(value) { return JSON.stringify(value, Object.keys(value).sort()); }

const entries = [];
for (const name of names) {
  try {
    const content = await readFile(join(root, name, "SKILL.md"));
    entries.push({ name, sourceSha: sha(content), source: `${name}/SKILL.md` });
  } catch (cause) {
    // A skill that is installed only in the host cache is not silently
    // copied into the release. It remains explicitly listed as pending so a
    // reviewer can supply a tracked source before publication.
    if (cause?.code !== "ENOENT") throw cause;
    entries.push({ name, sourceSha: null, source: null, status: "source_missing" });
  }
}
let sourceCommit = "unavailable";
try { ({ stdout: sourceCommit } = await run("git", ["-C", root, "rev-parse", "HEAD"])); sourceCommit = sourceCommit.trim(); } catch { /* source SHA remains explicit */ }
const manifest = {
  manifestVersion: 1,
  sourceCommit,
  runtime: { bridgeProtocol: "submit_event", storageVersion: 2 },
  defaults: { selfRegister: false, adminInit: false },
  entries,
  packageHash: sha(canonical({ manifestVersion: 1, sourceCommit, runtime: { bridgeProtocol: "submit_event", storageVersion: 2 }, defaults: { selfRegister: false, adminInit: false }, entries }))
};
const output = join(root, "dist");
await mkdir(output, { recursive: true });
await writeFile(join(output, "device-plugin-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
process.stdout.write(`${JSON.stringify({ packageHash: manifest.packageHash, entries: entries.length })}\n`);
