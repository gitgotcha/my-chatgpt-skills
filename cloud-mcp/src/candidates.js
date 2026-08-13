export class InputError extends Error {
  constructor(message) {
    super(message);
    this.code = "invalid_argument";
  }
}

export async function createCandidate(db, input, now, idFactory) {
  const displayName = input?.displayName?.trim();
  if (!displayName) throw new InputError("displayName is required");

  const candidateId = `CAND-${idFactory()}`;
  const distinguishingNote = input.distinguishingNote?.trim() ?? "";
  await db.prepare(
    "INSERT INTO candidates (candidate_id, display_name, distinguishing_note, created_at) VALUES (?, ?, ?, ?)"
  ).bind(candidateId, displayName, distinguishingNote, now).run();

  return {
    schemaVersion: "1.0",
    candidateId,
    displayName,
    distinguishingNote,
    createdAt: now
  };
}
