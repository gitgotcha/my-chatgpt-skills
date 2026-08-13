const encoder = new TextEncoder();

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
  const response = await fetchImpl("https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,mimeType", {
    method: "POST",
    headers: { authorization: `Bearer ${token}`, "content-type": `multipart/related; boundary=${boundary}` },
    body
  });
  const payload = await response.json();
  if (!response.ok || !payload.id) throw new Error("Google Drive write failed: missing file id");
  return payload;
}

async function googleGet(env, url, fetchImpl = fetch) {
  const token = await accessToken(env, fetchImpl);
  const response = await fetchImpl(url, { headers: { authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error("Google Drive read failed");
  return response;
}

async function listFoldersFromDrive(env, deps = {}) {
  const query = encodeURIComponent(`'${env.GOOGLE_DRIVE_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false`);
  const response = await googleGet(env, `https://www.googleapis.com/drive/v3/files?q=${query}&fields=files(id,name)`, deps.fetch ?? fetch);
  const payload = await response.json();
  return payload.files ?? [];
}

async function readCandidateFromDrive(env, folderId, deps = {}) {
  const query = encodeURIComponent(`'${folderId}' in parents and name = 'candidate.json' and trashed = false`);
  const list = await googleGet(env, `https://www.googleapis.com/drive/v3/files?q=${query}&fields=files(id)`, deps.fetch ?? fetch);
  const payload = await list.json();
  const fileId = payload.files?.[0]?.id;
  if (!fileId) throw new Error("Candidate metadata is missing in Google Drive");
  const file = await googleGet(env, `https://www.googleapis.com/drive/v3/files/${fileId}?alt=media`, deps.fetch ?? fetch);
  return file.json();
}

export async function uploadDriveFile(env, parentId, name, content, mimeType, deps = {}) {
  const uploadFile = deps.uploadFile ?? ((...args) => googleUpload(env, ...args, deps.fetch ?? fetch));
  const file = await uploadFile(parentId, name, content, mimeType);
  if (!file?.id) throw new Error("Google Drive write failed: missing file id");
  return file;
}

export async function createCandidateFolder(env, input, deps = {}) {
  const displayName = input?.displayName?.trim();
  if (!displayName) throw new Error("displayName is required");
  const candidateId = `CAND-${(deps.uuid ?? crypto.randomUUID)()}`;
  const createdAt = (deps.now ?? (() => new Date().toISOString()))();
  const distinguishingNote = input.distinguishingNote?.trim() ?? "";
  const createFolder = deps.createFolder ?? ((parentId, name) => googleUpload(env, parentId, name, "", "application/vnd.google-apps.folder", deps.fetch ?? fetch));
  const folder = await createFolder(env.GOOGLE_DRIVE_FOLDER_ID, candidateId);
  if (!folder?.id) throw new Error("Google Drive write failed: missing folder id");
  const candidate = { schemaVersion: "1.0", candidateId, displayName, distinguishingNote, createdAt, folderId: folder.id };
  await uploadDriveFile(env, folder.id, "candidate.json", JSON.stringify(candidate), "application/json", deps);
  return candidate;
}

export async function listCandidates(env, input = {}, deps = {}) {
  const listFolders = deps.listFolders ?? (() => listFoldersFromDrive(env, deps));
  const readCandidate = deps.readCandidate ?? ((folderId) => readCandidateFromDrive(env, folderId, deps));
  const query = input.query?.trim().toLowerCase() ?? "";
  const limit = Math.min(Math.max(Number(input.limit) || 20, 1), 100);
  const folders = await listFolders();
  const candidates = [];
  for (const folder of folders) {
    const candidate = await readCandidate(folder.id);
    if (!query || candidate.displayName.toLowerCase().includes(query) || candidate.candidateId.toLowerCase().includes(query)) candidates.push({ ...candidate, folderId: folder.id });
    if (candidates.length === limit) break;
  }
  return candidates;
}

export async function getCandidateContext(env, input, deps = {}) {
  const candidates = await listCandidates(env, { query: input.candidateId, limit: 100 }, deps);
  const candidate = candidates.find((item) => item.candidateId === input.candidateId);
  if (!candidate) throw new Error("Candidate not found in Google Drive");
  return { ...candidate, selectedDomain: input.selectedDomain ?? null, activeResumeId: input.resumeId ?? null, artifacts: [] };
}

export async function readArtifact(env, input, deps = {}) {
  const query = encodeURIComponent(`'${input.candidateFolderId}' in parents and name = '${input.artifactKey.replaceAll("'", "\\'")}' and trashed = false`);
  const list = await googleGet(env, `https://www.googleapis.com/drive/v3/files?q=${query}&fields=files(id,name,mimeType)`, deps.fetch ?? fetch);
  const payload = await list.json();
  const file = payload.files?.[0];
  if (!file?.id) throw new Error("Artifact not found in Google Drive");
  const content = await googleGet(env, `https://www.googleapis.com/drive/v3/files/${file.id}?alt=media`, deps.fetch ?? fetch);
  return { fileId: file.id, fileName: file.name, contentType: file.mimeType, content: await content.text() };
}
