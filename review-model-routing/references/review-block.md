# Embedded Review Gate

Instantiate every field; do not leave angle-bracket placeholders in a delivered plan. If a source path, command, or model lacks evidence, name it as a blocking input instead of inventing it.

```yaml
review:
  id: "R-01"
  tasks: ["T-01"]
  phase: "post_implementation"
  after: ["T-01"]
  blocks: ["T-02"]
  level: "standard"
  status: "pending"
  model: "gpt-5.6-sol"
  reasoning_effort: "medium"
  execution_mode: "automatic"
  reason: "Bounded behavior change requiring requirement and source review"
  inputs:
    - "Approved design: docs/superpowers/specs/example-design.md"
    - "Task T-01 diff and exact base commit"
    - "Task T-01 test command and captured result"
  checks:
    - "The observable behavior matches the approved acceptance criteria"
    - "The implementation does not expand the approved scope"
  pass_when:
    - "Every check has sufficient evidence and no blocker remains"
  on_failure: "Return to T-01, repair the affected scope, then rerun R-01"
  on_unavailable: "Pause R-01 unless a verified equally capable fallback exists"
```

Omit `reasoning_effort` when unsupported. Use `automatic` only with a verified dispatch mechanism; otherwise write `manual_handoff`. Pre-implementation inputs contain the design, current source, test design, and risk controls. Post-implementation inputs add the exact diff/version and actual verification output.

Attach an instantiated prompt:

> Review task T-01 at the post-implementation gate. Review only; do not modify code. Read the approved design, the T-01 diff against the named base commit, and the captured test result. Check each listed invariant. First assess the raw evidence independently, then compare the implementer's explanation. Return `pass`, `changes_required`, or `insufficient_evidence`. For every issue provide location, evidence, impact, blocking status, and a proposed verification method. Do not assume missing tests passed. The verdict applies only to the named input version.

For `critical` work, the pre-implementation gate blocks the implementation task. The post-implementation gate follows that task and blocks integration, release, or an explicit final delivery gate. Never create a dependency cycle. A combined review still returns one verdict per task.
