# reliable-drive-sync cloud MCP

This Worker exposes the candidate and artifact MCP contract to a cloud Codex task. It requires D1, R2, `MCP_BEARER_TOKEN`, `GOOGLE_SERVICE_ACCOUNT_JSON`, and `GOOGLE_DRIVE_FOLDER_ID` before deployment. Do not put any of these values in Git.

1. Create a D1 database and R2 bucket; replace `database_id` in `wrangler.toml`.
2. Share the target Drive folder with the Google service-account email.
3. Run `wrangler secret put MCP_BEARER_TOKEN`, `wrangler secret put GOOGLE_SERVICE_ACCOUNT_JSON`, and `wrangler secret put GOOGLE_DRIVE_FOLDER_ID`.
4. Run `wrangler d1 migrations apply reliable-drive-sync --remote`, then `wrangler deploy`.
5. Configure the published HTTPS endpoint as the `reliable-drive-sync` remote MCP in the eligible Codex workspace.
