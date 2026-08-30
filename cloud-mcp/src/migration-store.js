// Auditable, non-destructive migration of pre-normalization namespace data.
//
// The migration only ever reads the legacy directories and only ever writes new
// files below the canonical plugin root. Source objects are never updated,
// moved or deleted, and a target object that already exists with different
// content stops the run instead of being overwritten.
//
// dry-run  -> report what would happen, write nothing.
// execute  -> re-scan, prove the scan is unchanged via the approved plan hash,
//             then copy only what is missing and verify every content hash.

import { canonicalHash } from "./event-store.js";
import { normalizeDisplayName } from "./user-store.js";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const MIGRATION_SEGMENTS = [["events"], ["profile", "snapshots"]];
const COPY = "copy";
const SKIP = "skip";
const CONFLICT = "conflict";

const isUuid = (value) => typeof value === "string" && UUID.test(value);

export function createMigrationStore({
  legacyReader,
  layout,
  drive,
  userStore,
  now = () => new Date().toISOString(),
  uuid = () => crypto.randomUUID(),
  hash = canonicalHash
}) {
  if (!legacyReader?.path || !legacyReader?.registrations || !legacyReader?.readJson) throw new Error("invalid_migration_store");
  if (!layout?.findDomainPath || !layout?.ensureDomainPath || !layout?.ensureUserRoot) throw new Error("invalid_migration_store");
  if (!drive?.createJson || !drive?.readJson || !drive?.listJson) throw new Error("invalid_migration_store");

  /** Legacy user ids whose registration matches the normalised display name. */
  async function legacyUserIds(domain, name) {
    const records = await legacyReader.registrations(domain);
    const matched = records
      .filter((record) => isUuid(record.userId)
        && normalizeDisplayName(record.username ?? record.displayName) === name)
      .map((record) => record.userId);
    return [...new Set(matched)];
  }

  /** Enumerate every legacy object that belongs to the requested user. */
  async function scan({ identity, displayName, domains }) {
    const name = normalizeDisplayName(displayName);
    const items = [];
    for (const domain of domains) {
      for (const legacyUserId of await legacyUserIds(domain, name)) {
        for (const segments of MIGRATION_SEGMENTS) {
          const folder = await legacyReader.path({ domain, userId: legacyUserId, segments });
          if (!folder) continue;
          for (const file of await legacyReader.listJson(folder.id)) {
            const read = await legacyReader.readJson(file.id);
            if (!read || read.name !== file.name || !read.value) continue;
            items.push({
              domain,
              legacyUserId,
              sourceFileId: file.id,
              sourceName: file.name,
              segments,
              contentHash: await hash(read.value),
              source: `root/${domain}/users/${legacyUserId}/${segments.join("/")}/${file.name}`,
              target: `${layout.pluginRootName}/users/${identity.userId}/${domain}/${segments.join("/")}/${file.name}`
            });
          }
        }
      }
    }
    return items;
  }

  /**
   * Compare every source object against the canonical target. Identical content
   * is skipped, missing content is copied, and different content under the same
   * target key is a conflict that must never be overwritten.
   */
  async function resolveActions(identity, items) {
    const resolved = [];
    for (const item of items) {
      let action = COPY;
      const folder = await layout.findDomainPath(identity.userId, item.domain, item.segments);
      if (folder) {
        const existing = (await drive.listJson(folder.id)).find((file) => file.name === item.sourceName);
        if (existing) {
          const read = await drive.readJson(existing.id);
          const existingHash = read?.value ? await hash(read.value) : null;
          action = existingHash === item.contentHash ? SKIP : CONFLICT;
        }
      }
      resolved.push({ ...item, action });
    }
    return resolved;
  }

  // The approved hash covers the scan result only: which source objects exist,
  // where they would land and what they contain. Per-object actions are derived
  // from the live target state on every run, so they are deliberately excluded:
  // a completed migration re-scans to the same hash and replays as a no-op,
  // while a source or target that changed between dry-run and execute still
  // invalidates the approval (conflicts are then caught by resolveActions).
  const planHashOf = ({ name, userId, domains, items }) => hash({
    displayName: name,
    userId,
    domains,
    items: items.map(({ sourceFileId, target, contentHash }) => ({ sourceFileId, target, contentHash }))
  });

  async function buildPlan(identity, { displayName, domains }) {
    const name = normalizeDisplayName(displayName);
    const items = await resolveActions(identity, await scan({ identity, displayName: name, domains }));
    const planHash = await planHashOf({ name, userId: identity.userId, domains, items });
    const count = (action) => items.filter((item) => item.action === action).length;
    return {
      items,
      planHash,
      summary: { total: items.length, copy: count(COPY), skip: count(SKIP), conflict: count(CONFLICT) }
    };
  }

  async function validate(identity, { displayName, domains }) {
    const name = normalizeDisplayName(displayName);
    if (!name) throw new Error("invalid_display_name");
    if (!identity?.userId || !isUuid(identity.userId)) throw new Error("identity_mismatch");
    const allowed = legacyReader.domains ?? [];
    // Omitting domains means "every namespace that still holds legacy data".
    const requested = domains === undefined ? allowed : domains;
    if (!Array.isArray(requested) || requested.length === 0) throw new Error("invalid_migration_domains");
    if (requested.some((domain) => !allowed.includes(domain))) throw new Error("invalid_migration_domains");
    // Migration writes below the canonical user root, so the identity must be
    // a registered global user rather than an arbitrary id.
    if (userStore?.verify) {
      const checked = await userStore.verify({ userId: identity.userId, displayName: name });
      if (checked?.status !== "ok" || checked.identity?.userId !== identity.userId) throw new Error("identity_mismatch");
    }
    return { name, domains: [...requested] };
  }

  /** dry-run: report the plan without writing anything anywhere. */
  async function plan(identity, options = {}) {
    const { name, domains } = await validate(identity, options);
    const { items, planHash, summary } = await buildPlan(identity, { ...options, displayName: name, domains });
    return {
      status: "ok",
      mode: "dry-run",
      migrationId: uuid(),
      displayName: name,
      userId: identity.userId,
      domains,
      items,
      summary,
      planHash
    };
  }

  /**
   * execute: re-scan and prove nothing changed since the approved plan before
   * copying. Conflicts stop the run before any file is written.
   */
  async function execute(identity, options = {}) {
    const { migrationId, approvedPlanHash } = options;
    if (!isUuid(migrationId)) throw new Error("invalid_migration_id");
    if (typeof approvedPlanHash !== "string" || !approvedPlanHash) throw new Error("migration_plan_required");
    const { name, domains } = await validate(identity, options);

    const startedAt = now();
    const { items, planHash, summary } = await buildPlan(identity, { ...options, displayName: name, domains });
    if (planHash !== approvedPlanHash) throw new Error("migration_plan_stale");
    if (summary.conflict > 0) throw new Error("migration_conflict");

    const copied = [];
    for (const item of items.filter((candidate) => candidate.action === COPY)) {
      const folder = await layout.ensureDomainPath(identity.userId, item.domain, item.segments);
      const source = await legacyReader.readJson(item.sourceFileId);
      if (!source?.value) throw new Error("migration_source_unreadable");
      const created = await drive.createJson(folder.id, item.sourceName, source.value);
      const read = await drive.readJson(created.id);
      const copiedHash = read?.value ? await hash(read.value) : null;
      if (!read || read.name !== item.sourceName || copiedHash !== item.contentHash) throw new Error("migration_hash_mismatch");
      copied.push({ ...item, action: "copied", targetFileId: read.id });
    }

    const receipt = {
      schemaVersion: "1.2",
      migrationId,
      mode: "execute",
      displayName: name,
      userId: identity.userId,
      domains,
      planHash: approvedPlanHash,
      startedAt,
      finishedAt: now(),
      summary: { ...summary, copied: copied.length },
      items: items.map((item) => ({
        source: item.source,
        target: item.target,
        contentHash: item.contentHash,
        action: item.action === COPY ? "copied" : item.action
      }))
    };

    const userRoot = await layout.ensureUserRoot(identity.userId);
    const receiptName = `migration-${migrationId}-receipt.json`;
    const created = await drive.createJson(userRoot.id, receiptName, receipt);
    const read = await drive.readJson(created.id);
    if (!read || read.name !== receiptName) throw new Error("migration_receipt_failed");

    return {
      status: "ok",
      mode: "execute",
      migrationId,
      planHash: approvedPlanHash,
      summary: receipt.summary,
      items: receipt.items,
      receipt,
      receiptFile: { fileId: read.id, name: read.name }
    };
  }

  return { plan, execute };
}
