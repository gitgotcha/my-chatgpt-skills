# reliable-drive-sync cloud MCP

This Worker exposes the candidate and artifact MCP contract to a cloud Codex task. It writes directly to one service-account-shared Google Drive folder. It reports success only after Google Drive returns a file or folder ID; any Drive error is returned to the caller and stops the persistence workflow. Do not put secrets in Git.

1. Create a Drive folder and share it with the Google service-account email as an editor.
2. Run `wrangler secret put MCP_BEARER_TOKEN`, `wrangler secret put GOOGLE_SERVICE_ACCOUNT_JSON`, and `wrangler secret put GOOGLE_DRIVE_FOLDER_ID`.
3. Run `wrangler deploy`.
4. Configure the published HTTPS endpoint as the `reliable-drive-sync` remote MCP in the eligible Codex workspace.

Candidate creation writes a candidate folder and a `candidate.json` file before it returns. Artifact and event writes use the confirmed candidate folder ID and return only after the Drive upload succeeds.
