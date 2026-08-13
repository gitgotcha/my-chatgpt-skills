CREATE TABLE candidates (
  candidate_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  distinguishing_note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);

CREATE TABLE artifacts (
  candidate_id TEXT NOT NULL,
  artifact_key TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  storage_key TEXT NOT NULL,
  sync_state TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL,
  PRIMARY KEY (candidate_id, artifact_key)
);

CREATE TABLE events (
  event_key TEXT PRIMARY KEY,
  candidate_id TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL
);
