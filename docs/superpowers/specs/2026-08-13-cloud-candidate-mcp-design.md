# Cloud Candidate MCP Design

Cloud Codex tasks start from this repository and use `AGENTS.md` to load exactly one existing skill. Candidate and artifact persistence is provided by an authenticated Cloudflare Worker MCP. Candidate metadata lives in D1 and immutable artifact bytes belong in R2; Drive access is available only through Worker secrets and a service-account-shared folder.

`create_candidate` returns a new `CAND-` summary. The user must explicitly confirm that returned ID before the interview skills read detailed context or submit records. Duplicate display names create different candidate IDs rather than merging identities.

Deployment requires Cloudflare bindings plus `MCP_BEARER_TOKEN`, `GOOGLE_SERVICE_ACCOUNT_JSON`, and `GOOGLE_DRIVE_FOLDER_ID`; no secret is committed to the repository.
