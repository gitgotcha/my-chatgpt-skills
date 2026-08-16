# Google Drive OAuth Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add OAuth refresh-token Drive authentication so ordinary My Drive folders can receive identity and interview events.

**Architecture:** The Drive repository keeps its public interface unchanged. A token provider selects OAuth refresh-token credentials when configured and otherwise uses the existing service-account JWT provider; all Drive upload/list/read calls reuse the selected bearer token.

**Tech Stack:** Cloudflare Worker JavaScript, Web Crypto, Google OAuth token endpoint, Google Drive REST API, Node test runner.

## Global Constraints

- Preserve the MCP `submit_event` envelope and `algorithm` namespace unchanged.
- Never log or commit `GOOGLE_OAUTH_CLIENT_SECRET` or `GOOGLE_OAUTH_REFRESH_TOKEN`.
- Keep service-account authentication as a fallback for existing deployments.
- Use only `GOOGLE_DRIVE_FOLDER_ID` for the existing Drive root.

---

### Task 1: Add OAuth token-provider coverage

**Files:**
- Modify: `cloud-mcp/test/google-drive.test.js`
- Modify: `cloud-mcp/src/google-drive.js`

**Interfaces:**
- Consumes: Worker env with OAuth secrets or service-account JSON and injected `fetch`.
- Produces: `createDriveRepository(env, { fetch })` calls Google token endpoint with OAuth refresh credentials when configured.

- [x] Write failing tests for OAuth exchange, OAuth preference, fallback, and token failure.
- [x] Run focused tests and observe the expected missing OAuth behavior.
- [x] Implement the minimal OAuth provider and preserve the existing JWT provider.
- [x] Run focused tests and full Node tests.

### Task 2: Deploy OAuth secrets

**Files:**
- Modify: Cloudflare Worker secrets only; no source files.

**Interfaces:**
- Consumes: local OAuth client JSON and `token.txt`.
- Produces: Worker secrets `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REFRESH_TOKEN`.

- [x] Read only the required fields locally without printing them.
- [x] Upload each value with `wrangler secret put` through stdin.
- [x] Keep the existing service-account secret untouched.

### Task 3: Live validation and regression

- [x] Deploy the Worker code.
- [x] Call read-only `identity.list`.
- [x] Call `identity.create` for `乔炳源` and read back `identity.list`.
- [x] Run `npm test --prefix cloud-mcp` and all three Python suites.
