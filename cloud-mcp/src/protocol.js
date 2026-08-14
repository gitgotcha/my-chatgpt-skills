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
  if (!ALLOWED_NAMESPACES.has(input.namespace)) {
    throw new ProtocolError("invalid_namespace");
  }
  if (!ALLOWED_EVENT_TYPES.has(input.eventType)) {
    throw new ProtocolError("invalid_event_type");
  }
  if (typeof input.requestId !== "string" || !input.requestId.trim()) {
    throw new ProtocolError("invalid_request_id");
  }
  if (input.payload !== undefined && (input.payload === null || Array.isArray(input.payload) || typeof input.payload !== "object")) {
    throw new ProtocolError("invalid_payload");
  }
  return structuredClone(input);
}
