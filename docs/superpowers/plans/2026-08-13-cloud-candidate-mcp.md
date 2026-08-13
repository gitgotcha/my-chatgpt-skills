# Cloud Candidate MCP Implementation Plan

**Goal:** provide cloud task routing and a `reliable-drive-sync` candidate-creation MCP.

1. Create an isolated Worker package with D1/R2 configuration and migrations.
2. Test candidate creation before implementing it; ensure blank names fail and same names remain distinct IDs.
3. Test and implement authenticated MCP negotiation, tool discovery, and `create_candidate`.
4. Add root routing instructions and require confirmation of newly created candidate IDs in the interview skills.
5. Configure Cloudflare secrets, apply migrations, deploy the Worker, and register the endpoint as a remote MCP in an eligible workspace.
