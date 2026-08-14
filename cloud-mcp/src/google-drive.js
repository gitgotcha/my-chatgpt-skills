const encoder = new TextEncoder();

export const formatGoogleDriveWriteError = (status, payload) => {
  const message = payload?.error?.message;
  return typeof message === "string" && message.trim()
    ? `Google Drive write failed (${status}): ${message.trim()}`
    : `Google Drive write failed (${status})`;
};

export const withSharedDriveSupport = (rawUrl, { list = false } = {}) => {
  const url = new URL(rawUrl);
  url.searchParams.set("supportsAllDrives", "true");
  if (list) {
    url.searchParams.set("includeItemsFromAllDrives", "true");
    url.searchParams.set("corpora", "allDrives");
  }
  return url.toString();
};

const base64url = (value) => {
  const bytes = typeof value === "string" ? encoder.encode(value) : new Uint8Array(value);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
};

async function accessToken(env, fetchImpl = fetch) {
  const serviceAccount = JSON.parse(env.GOOGLE_SERVICE_ACCOUNT_JSON);
  const now = Math.floor(Date.now() / 1000);
  const header = base64url(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const claim = base64url(JSON.stringify({
    iss: serviceAccount.client_email,
    scope: "https://www.googleapis.com/auth/drive",
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600
  }));
  const privateKey = serviceAccount.private_key.replace(/-----[^-]+-----|\s/g, "");
  const keyBytes = Uint8Array.from(atob(privateKey), (character) => character.charCodeAt(0));
  const key = await crypto.subtle.importKey("pkcs8", keyBytes, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]);
  const signature = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", key, encoder.encode(`${header}.${claim}`));
  const response = await fetchImpl("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer", assertion: `${header}.${claim}.${base64url(signature)}` })
  });
  const payload = await response.json();
  if (!response.ok || !payload.access_token) throw new Error("Google OAuth token request failed");
  return payload.access_token;
}

async function googleUpload(env, parentId, name, content, mimeType, fetchImpl = fetch) {
  const token = await accessToken(env, fetchImpl);
  const boundary = "drive-mcp-boundary";
  const metadata = JSON.stringify({ name, parents: [parentId], mimeType });
  const body = `--${boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n${metadata}\r\n--${boundary}\r\nContent-Type: ${mimeType}\r\n\r\n${content}\r\n--${boundary}--`;
  const response = await fetchImpl(withSharedDriveSupport("https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,mimeType"), {
    method: "POST",
    headers: { authorization: `Bearer ${token}`, "content-type": `multipart/related; boundary=${boundary}` },
    body
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(formatGoogleDriveWriteError(response.status, payload));
  if (!payload.id) throw new Error("Google Drive write failed: missing file id");
  return payload;
}

async function googleGet(env, url, fetchImpl = fetch, options = {}) {
  const token = await accessToken(env, fetchImpl);
  const response = await fetchImpl(withSharedDriveSupport(url, options), { headers: { authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error("Google Drive read failed");
  return response;
}

const escapeDriveQuery = (value) => value.replaceAll("\\", "\\\\").replaceAll("'", "\\'");

const driveFields = "id,name,mimeType,parents,createdTime";

const requiredParentId = (parentId) => {
  if (!parentId) throw new Error("parentId is required");
  return parentId;
};

export function createDriveRepository(env, deps = {}) {
  const fetchImpl = deps.fetch ?? fetch;
  const createFolderImpl = deps.createFolder ?? ((parentId, name) =>
    googleUpload(env, parentId, name, "", "application/vnd.google-apps.folder", fetchImpl));
  const uploadFileImpl = deps.uploadFile ?? ((parentId, name, content, mimeType) =>
    googleUpload(env, parentId, name, content, mimeType, fetchImpl));
  const listChildrenImpl = deps.listChildren ?? (async (parentId, options = {}) => {
    const clauses = [`'${escapeDriveQuery(requiredParentId(parentId))}' in parents`, "trashed = false"];
    if (options.name) clauses.push(`name = '${escapeDriveQuery(options.name)}'`);
    if (options.foldersOnly) clauses.push("mimeType = 'application/vnd.google-apps.folder'");
    if (options.jsonOnly) clauses.push("mimeType = 'application/json'");
    const query = encodeURIComponent(clauses.join(" and "));
    const response = await googleGet(env, `https://www.googleapis.com/drive/v3/files?q=${query}&orderBy=createdTime&fields=files(${driveFields})`, fetchImpl, { list: true });
    const payload = await response.json();
    return payload.files ?? [];
  });
  const readJsonFileImpl = deps.readJsonFile ?? (async (fileId) => {
    const id = requiredParentId(fileId);
    const metadataResponse = await googleGet(env, `https://www.googleapis.com/drive/v3/files/${encodeURIComponent(id)}?fields=${driveFields}`, fetchImpl);
    const metadata = await metadataResponse.json();
    if (!metadata?.id) throw new Error("Google Drive read failed: missing file id");
    const contentResponse = await googleGet(env, `https://www.googleapis.com/drive/v3/files/${encodeURIComponent(id)}?alt=media`, fetchImpl);
    return { ...metadata, value: JSON.parse(await contentResponse.text()) };
  });

  return {
    rootFolderId: env.GOOGLE_DRIVE_FOLDER_ID,
    async listChildren(parentId, options = {}) {
      requiredParentId(parentId);
      return listChildrenImpl(parentId, options);
    },
    async findFolder(parentId, name) {
      if (!name) throw new Error("folder name is required");
      const matches = await this.listChildren(parentId, { name, foldersOnly: true });
      return matches[0] ?? null;
    },
    async ensureFolder(parentId, name) {
      if (!parentId || !name || name.includes("/") || name.includes("\\")) throw new Error("invalid folder input");
      const existing = await this.findFolder(parentId, name);
      if (existing) return existing;
      const created = await createFolderImpl(parentId, name);
      if (!created?.id) throw new Error("Google Drive write failed: missing folder id");
      return { ...created, name, parents: [parentId] };
    },
    async createJson(parentId, name, value) {
      if (!parentId) throw new Error("parentId is required");
      if (!/^((identity)|(registration-[0-9a-f-]+)|(event-[0-9a-f-]+)|(snapshot-[0-9TZ:.-]+-[0-9a-f-]+))\.json$/i.test(name)) {
        throw new Error("invalid JSON target");
      }
      const file = await uploadFileImpl(parentId, name, JSON.stringify(value), "application/json");
      if (!file?.id) throw new Error("Google Drive write failed: missing file id");
      return this.readJson(file.id);
    },
    async readJson(fileId) {
      return readJsonFileImpl(fileId);
    },
    async listJson(parentId) {
      const children = await this.listChildren(parentId, { jsonOnly: true });
      return children.filter((file) => file.mimeType === "application/json");
    }
  };
}
