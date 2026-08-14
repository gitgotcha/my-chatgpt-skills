const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const encoder = new TextEncoder();

export function canonicalJson(value) {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
}

function contentForHash(event) {
  const clone = structuredClone(event);
  delete clone.contentHash;
  return clone;
}

export async function canonicalHash(event) {
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(canonicalJson(contentForHash(event))));
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

const hasOnlyParent = (file, parentId) => Array.isArray(file?.parents) && file.parents.length === 1 && file.parents[0] === parentId;
const validId = (value) => typeof value === "string" && UUID.test(value);

export function createEventStore({ namespace = "interview", namespaceStore, drive, canonicalHash: hash = canonicalHash }) {
  if (!namespaceStore?.verifyIdentity || !drive?.rootFolderId) throw new Error("invalid_event_store");
  if (!new Set(["algorithm", "interview"]).has(namespace)) throw new Error("invalid_namespace");

  async function verify(identity) {
    const result = await namespaceStore.verifyIdentity(identity);
    if (result?.status !== "ok" || result.identity?.userId !== identity?.userId || result.identity?.username !== identity?.username) throw new Error("identity_mismatch");
    return result.identity;
  }

  async function eventFolder(identity, create) {
    const namespaceRoot = create ? await drive.ensureFolder(drive.rootFolderId, namespace) : await drive.findFolder(drive.rootFolderId, namespace);
    const users = namespaceRoot && (create ? await drive.ensureFolder(namespaceRoot.id, "users") : await drive.findFolder(namespaceRoot.id, "users"));
    const user = users && (create ? await drive.ensureFolder(users.id, identity.userId) : await drive.findFolder(users.id, identity.userId));
    const events = user && (create ? await drive.ensureFolder(user.id, "events") : await drive.findFolder(user.id, "events"));
    return events && hasOnlyParent(events, user.id) ? events : null;
  }

  async function validEvent(file, parentId, identity) {
    if (!file || !hasOnlyParent(file, parentId) || !/^event-[0-9a-f-]+\.json$/i.test(file.name)) return null;
    const read = await drive.readJson(file.id);
    const event = read?.value;
    if (!hasOnlyParent(read, parentId) || read.name !== file.name || !event || event.schemaVersion !== "1.2"
      || !validId(event.eventId) || read.name !== `event-${event.eventId}.json` || typeof event.eventKey !== "string" || !event.eventKey
      || typeof event.eventType !== "string" || !event.eventType || event.userId !== identity.userId || event.username !== identity.username
      || typeof event.contentHash !== "string" || event.contentHash !== await hash(event)) return null;
    return { event: structuredClone(event), file: read };
  }

  async function verifiedEventRecords(identity) {
    const verifiedIdentity = await verify(identity);
    const folder = await eventFolder(verifiedIdentity, false);
    if (!folder) return [];
    const files = await drive.listJson(folder.id);
    const verified = await Promise.all(files.map((file) => validEvent(file, folder.id, verifiedIdentity)));
    return verified.filter(Boolean);
  }

  async function listVerifiedEvents(identity) {
    return (await verifiedEventRecords(identity)).map(({ event }) => event);
  }

  function validateInput(identity, event) {
    if (!event || event.schemaVersion !== "1.2" || !validId(event.eventId) || typeof event.eventKey !== "string" || !event.eventKey
      || typeof event.eventType !== "string" || !event.eventType || event.userId !== identity.userId || event.username !== identity.username) throw new Error("invalid_event");
  }

  async function appendEvent(identity, input) {
    const verifiedIdentity = await verify(identity);
    validateInput(verifiedIdentity, input);
    const event = structuredClone(input);
    event.contentHash = await hash(event);
    const existing = await verifiedEventRecords(verifiedIdentity);
    const duplicate = existing.find(({ event: candidate }) => candidate.eventKey === event.eventKey);
    if (duplicate) {
      if (duplicate.event.contentHash !== event.contentHash) throw new Error("event_key_conflict");
      return { event: duplicate.event, receipt: { fileId: duplicate.file.id, eventId: duplicate.event.eventId, eventKey: duplicate.event.eventKey } };
    }
    const folder = await eventFolder(verifiedIdentity, true);
    if ((await drive.listJson(folder.id)).some((file) => file.name === `event-${event.eventId}.json`)) throw new Error("event_id_conflict");
    const created = await drive.createJson(folder.id, `event-${event.eventId}.json`, event);
    const checked = await validEvent(created, folder.id, verifiedIdentity);
    if (!checked || checked.event.eventId !== event.eventId || checked.event.eventKey !== event.eventKey || checked.event.contentHash !== event.contentHash) throw new Error("event_readback_failed");
    return { event: checked.event, receipt: { fileId: checked.file.id, eventId: event.eventId, eventKey: event.eventKey } };
  }

  return { appendEvent, listVerifiedEvents };
}
