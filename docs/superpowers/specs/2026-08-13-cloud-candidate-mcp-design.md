# Cloud Candidate MCP Design

Cloud Codex tasks start from this repository and use `AGENTS.md` to load exactly one existing skill. Candidate and artifact persistence is provided by an authenticated Cloudflare Worker MCP. The Worker writes candidate directories, candidate metadata, and interview artifacts directly to a single service-account-shared Google Drive folder; Drive access is available only through Worker secrets.

`create_candidate` returns a new `CAND-` summary. The user must explicitly confirm that returned ID before the interview skills read detailed context or submit records. Duplicate display names create different candidate IDs rather than merging identities.

Each write returns success only after the Google Drive API returns the created file or folder identity. Any Drive API failure is returned as an MCP error and the calling workflow stops instead of continuing with a pending state. The direct mode has no D1 database, R2 bucket, queue, hash comparison, asynchronous synchronizer, or retry state.

Deployment requires `MCP_BEARER_TOKEN`, `GOOGLE_SERVICE_ACCOUNT_JSON`, and `GOOGLE_DRIVE_FOLDER_ID`; no secret is committed to the repository.
