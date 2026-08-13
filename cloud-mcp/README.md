# reliable-drive-sync cloud MCP

This Worker exposes a simple name-folder MCP contract to a cloud Codex task. It writes directly to one service-account-shared Google Drive folder. A `displayName` maps to a same-name folder under that root: an existing folder is reused, and a missing one is created. It reports success only after Google Drive returns a file or folder ID; any Drive error is returned to the caller and stops the persistence workflow. Do not put secrets in Git.

1. Create a Drive folder and share it with the Google service-account email as an editor.
2. Run `wrangler secret put MCP_BEARER_TOKEN`, `wrangler secret put GOOGLE_SERVICE_ACCOUNT_JSON`, and `wrangler secret put GOOGLE_DRIVE_FOLDER_ID`.
3. Run `wrangler deploy`.
4. Configure the published HTTPS endpoint as the `reliable-drive-sync` remote MCP in the eligible Codex workspace.

Call `find_or_create_candidate({ displayName })` before working with a user. It returns the Drive folder after finding the exact-name folder or creating `<displayName>/identity.json`. `get_candidate_context`, `read_artifact`, `submit_artifact`, and `submit_event` all take `displayName`; they resolve that same Drive folder themselves. There is no candidate ID, registry, database, queue, or asynchronous sync step.
