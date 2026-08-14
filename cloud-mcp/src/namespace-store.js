const NAMESPACES = new Set(["algorithm", "interview"]);
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const REGISTRATION = /^registration-([0-9a-f-]+)\.json$/i;

const normalizeUsername = (value) => typeof value === "string" ? value.normalize("NFKC").trim() : "";
const hasOnlyParent = (file, parentId) => Array.isArray(file?.parents) && file.parents.length === 1 && file.parents[0] === parentId;
const isUuid = (value) => typeof value === "string" && UUID.test(value);

export function createNamespaceStore({ namespace, drive, now = () => new Date().toISOString(), uuid = () => crypto.randomUUID() }) {
  if (!NAMESPACES.has(namespace)) throw new Error("invalid_namespace");
  if (!drive?.rootFolderId) throw new Error("invalid_drive");

  async function roots({ create }) {
    const root = create
      ? await drive.ensureFolder(drive.rootFolderId, namespace)
      : await drive.findFolder(drive.rootFolderId, namespace);
    if (!root) return null;
    const registry = create ? await drive.ensureFolder(root.id, "user-registry") : await drive.findFolder(root.id, "user-registry");
    const users = create ? await drive.ensureFolder(root.id, "users") : await drive.findFolder(root.id, "users");
    return registry && users ? { root, registry, users } : null;
  }

  function validRegistration(file, registryId) {
    const record = file?.value;
    const filename = REGISTRATION.exec(file?.name ?? "");
    return filename && filename[1].toLowerCase() === record?.userId?.toLowerCase() && hasOnlyParent(file, registryId)
      && record?.schemaVersion === "1.2" && record.status === "active" && isUuid(record.userId)
      && normalizeUsername(record.username) === record.username && record.username.length > 0
      && typeof record.createdAt === "string" && record.createdAt.length > 0;
  }

  async function registrations() {
    const location = await roots({ create: false });
    if (!location) return [];
    const files = location.registry ? await drive.listJson(location.registry.id) : [];
    const records = await Promise.all(files.filter((file) => REGISTRATION.test(file.name)).map(async (file) => {
      const read = await drive.readJson(file.id);
      return validRegistration(read, location.registry.id) ? read.value : null;
    }));
    return records.filter(Boolean).sort((left, right) => left.createdAt.localeCompare(right.createdAt));
  }

  async function verifyIdentity({ userId, username }) {
    const normalizedUsername = normalizeUsername(username);
    if (!isUuid(userId) || !normalizedUsername) throw new Error("identity_mismatch");
    const location = await roots({ create: false });
    if (!location) throw new Error("identity_mismatch");
    const matches = (await drive.listChildren(location.users.id, { name: userId, foldersOnly: true }))
      .filter((folder) => folder.name === userId && hasOnlyParent(folder, location.users.id));
    if (matches.length !== 1) throw new Error("identity_mismatch");
    const identities = (await drive.listJson(matches[0].id)).filter((file) => file.name === "identity.json");
    if (identities.length !== 1) throw new Error("identity_mismatch");
    const identity = await drive.readJson(identities[0].id);
    if (!hasOnlyParent(identity, matches[0].id) || identity.value?.schemaVersion !== "1.2"
      || identity.value.userId !== userId || normalizeUsername(identity.value.username) !== normalizedUsername
      || identity.value.username !== normalizedUsername) throw new Error("identity_mismatch");
    return { status: "ok", identity: { userId, username: normalizedUsername, verified: true } };
  }

  async function createIdentity({ username }) {
    const normalizedUsername = normalizeUsername(username);
    if (!normalizedUsername) throw new Error("invalid_username");
    if ((await registrations()).some((record) => record.username === normalizedUsername)) throw new Error("username_conflict");
    const location = await roots({ create: true });
    const userId = uuid();
    if (!isUuid(userId)) throw new Error("invalid_user_id");
    const user = await drive.ensureFolder(location.users.id, userId);
    await drive.ensureFolder(user.id, "events");
    const profile = await drive.ensureFolder(user.id, "profile");
    await drive.ensureFolder(profile.id, "snapshots");
    const createdAt = now();
    await drive.createJson(user.id, "identity.json", { schemaVersion: "1.2", userId, username: normalizedUsername, createdAt });
    await verifyIdentity({ userId, username: normalizedUsername });
    if ((await registrations()).some((record) => record.username === normalizedUsername)) throw new Error("username_conflict");
    const registration = await drive.createJson(location.registry.id, `registration-${userId}.json`, {
      schemaVersion: "1.2", userId, username: normalizedUsername, status: "active", createdAt
    });
    if (!validRegistration(registration, location.registry.id) || registration.value.userId !== userId) throw new Error("identity_mismatch");
    return { status: "ok", identity: { userId, username: normalizedUsername, verified: true } };
  }

  return {
    async listIdentities() { return { status: "ok", data: { registrations: await registrations() } }; },
    createIdentity,
    verifyIdentity
  };
}
