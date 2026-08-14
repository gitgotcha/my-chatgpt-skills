export const SCHEMA_VERSION = "1.2";
export const ALLOWED_NAMESPACES = new Set(["algorithm", "interview"]);
export const ALLOWED_EVENT_TYPES = new Set([
  "identity.list",
  "identity.create",
  "identity.verify",
  "algorithm.learning.completed",
  "interview.session.list",
  "interview.session.load",
  "interview.session.completed",
  "interview.review.completed"
]);
const ALLOWED_ENVELOPE_FIELDS = new Set(["schemaVersion", "namespace", "eventType", "identity", "payload", "requestId"]);
const PAYLOAD_FIELDS = new Map([
  ["identity.list", []],
  ["identity.create", ["username"]],
  ["identity.verify", ["userId", "username"]],
  ["interview.session.list", ["userId", "username"]],
  ["interview.session.load", ["userId", "username", "sessionId"]],
  ["interview.session.completed", ["userId", "username", "event"]],
  ["interview.review.completed", ["userId", "username", "event"]],
  ["algorithm.learning.completed", ["event"]]
]);

export class ProtocolError extends Error {
  constructor(status, message = status) {
    super(message);
    this.status = status;
  }
}

export function validateEnvelope(input) {
  if (!input || input.schemaVersion !== SCHEMA_VERSION) {
    throw new ProtocolError("invalid_schema_version");
  }
  if (Object.keys(input).some((field) => !ALLOWED_ENVELOPE_FIELDS.has(field))) {
    throw new ProtocolError("invalid_envelope");
  }
  if (!ALLOWED_NAMESPACES.has(input.namespace)) {
    throw new ProtocolError("invalid_namespace");
  }
  if (!ALLOWED_EVENT_TYPES.has(input.eventType)) {
    throw new ProtocolError("invalid_event_type");
  }
  if (input.eventType.startsWith("interview.") && input.namespace !== "interview") {
    throw new ProtocolError("invalid_event_type");
  }
  if (input.eventType.startsWith("algorithm.") && input.namespace !== "algorithm") {
    throw new ProtocolError("invalid_event_type");
  }
  if (typeof input.requestId !== "string" || !input.requestId.trim()) {
    throw new ProtocolError("invalid_request_id");
  }
  if (input.identity !== undefined && (input.identity === null || Array.isArray(input.identity)
    || typeof input.identity !== "object" || Object.keys(input.identity).some((field) => !["userId", "username"].includes(field))
    || Object.keys(input.identity).length !== 2 || typeof input.identity.userId !== "string" || !input.identity.userId.trim()
    || typeof input.identity.username !== "string" || !input.identity.username.trim())) {
    throw new ProtocolError("invalid_identity");
  }
  if (input.eventType === "algorithm.learning.completed" && input.identity === undefined) {
    throw new ProtocolError("invalid_identity");
  }
  if (input.payload !== undefined && (input.payload === null || Array.isArray(input.payload) || typeof input.payload !== "object")) {
    throw new ProtocolError("invalid_payload");
  }
  const allowedPayloadFields = PAYLOAD_FIELDS.get(input.eventType);
  if (!allowedPayloadFields || Object.keys(input.payload ?? {}).length !== allowedPayloadFields.length
    || Object.keys(input.payload ?? {}).some((field) => !allowedPayloadFields.includes(field))) {
    throw new ProtocolError("invalid_payload");
  }
  return structuredClone(input);
}
