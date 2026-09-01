# ChatGPT Work Reliable Drive Sync Tunnel Plan

## Objective

Provide a safe development-mode path from ChatGPT Work to the existing
Reliable Drive Sync stdio bridge using OpenAI Secure MCP Tunnel.

## Tasks

1. Add failing bridge tests for schema parity, configuration-late binding, and
   delivery failure behavior.
2. Fix the bridge to advertise the Worker identity contract and initialize
   without delivery configuration.
3. Add failing launcher tests for persistent Windows environment fallback and
   secret-safe output.
4. Update `start.cmd` to load missing values from `HKCU\\Environment` without
   logging them.
5. Add a tested PowerShell tunnel setup helper that validates inputs, initializes
   the stdio profile, runs `doctor`, and leaves `run` explicit.
6. Document the ChatGPT Work developer-mode connection and the account-bound
   `tunnel_id`/API-key steps.
7. Run bridge tests, Worker tests, layout checks, and repository status review.
8. Commit the implementation on the isolated feature branch and report the one
   remaining manual action: create/select the OpenAI tunnel in ChatGPT Work.

## Non-goals

- No public unauthenticated MCP endpoint.
- No OAuth implementation in this phase.
- No changes to Drive paths, event schemas, or profile projection logic.
- No secrets or user-specific paths in git.
