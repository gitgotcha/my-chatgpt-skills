# Google Drive OAuth Authentication Design

## Goal

Allow the reliable-drive-sync Worker to write to the user's ordinary My Drive when a Shared Drive is unavailable, without changing the MCP `submit_event` contract or algorithm-learning event paths.

## Design

`cloud-mcp/src/google-drive.js` will choose OAuth refresh-token authentication when all three secrets `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, and `GOOGLE_OAUTH_REFRESH_TOKEN` are present. It will POST those credentials to Google's token endpoint, use the returned access token for the existing Drive REST calls, and retain the current service-account JWT path as a backward-compatible fallback when OAuth secrets are absent.

No namespace, event validation, folder layout, or MCP envelope changes are made. `GOOGLE_DRIVE_FOLDER_ID` remains the root folder. OAuth secrets are Cloudflare Worker secrets only and never enter source control or logs.

## Failure and security

Missing or incomplete OAuth configuration falls back to the existing service-account path. A non-2xx token response fails closed with a generic token error. Google error bodies are used only for Drive write diagnostics; credentials are never included in errors.

## Verification

Unit tests cover OAuth token exchange, OAuth preference, service-account fallback, and token failure. The existing full Node suite and algorithm/conducting/reviewing Python suites must remain green. After deployment, `identity.create` and `identity.list` are the live write/read smoke test.
