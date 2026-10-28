# RDS-JBryon interview snapshot schemas

This schema is a content contract for JSON stored in readable RDS-JBryon routes. It is not an event envelope or an account/identity protocol. The user selects a route such as `project/12306/学习快照.json`; the Skill never asks for a user UUID, node ID, workspace epoch, or account registration.

The `SessionSnapshot` preserves interview questions, original answers, follow-ups, and project evidence. `ReviewSnapshot` stores assessments and any profile changes as separate data. Project-specific assessments remain in the selected project's snapshot and must not be duplicated into a global profile. A local JSON or DOCX report is a derived output and cannot prove that RDS accepted or projected a write.

The paired schema and manifest in `reviewing-java-backend-interviews/schemas/` must remain byte-identical. Do not reintroduce `Identity`, `Registration`, `ProfileSnapshot`, `userId`, `eventKey`, or `eventType` DTOs.
