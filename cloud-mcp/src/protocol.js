export const SCHEMA_VERSION = "1.2";
export const ALLOWED_NAMESPACES = new Set(["system", "algorithm", "interview", "resume-knowledge"]);
export const ALLOWED_EVENT_TYPES = new Set([
  "system.user-registered",
  "system.legacy-migration-requested",
  "algorithm.learning.completed",
  "algorithm.daily-plan-created",
  "interview.session.list",
  "interview.session.load",
  "interview.session.completed",
  "interview.review.completed",
  "resume-knowledge.resume-ingested",
  "resume-knowledge.claim-confirmed",
  "resume-knowledge.claim-rejected",
  "resume-knowledge.question-bank-created",
  "resume-knowledge.daily-plan-created",
  "resume-knowledge.answer-scored"
]);
const ALLOWED_ENVELOPE_FIELDS = new Set(["schemaVersion", "namespace", "eventType", "identity", "payload", "requestId"]);
const IDENTITY_FIELDS = new Set(["userId", "username"]);
const LEGACY_MODES = new Set(["dry-run", "execute"]);
const COMMON_OPTIONAL = ["userId", "username"];
const PAYLOAD_SCHEMA = new Map([
  ["system.user-registered", { required: ["displayName"], optional: [...COMMON_OPTIONAL] }],
  ["system.legacy-migration-requested", { required: ["displayName", "mode"], optional: [...COMMON_OPTIONAL, "domains"] }],
  ["algorithm.learning.completed", { required: ["event"], optional: [...COMMON_OPTIONAL] }],
  ["algorithm.daily-plan-created", { required: ["event"], optional: [...COMMON_OPTIONAL] }],
  ["interview.session.list", { required: [], optional: [...COMMON_OPTIONAL] }],
  ["interview.session.load", { required: ["sessionId"], optional: [...COMMON_OPTIONAL] }],
  ["interview.session.completed", { required: ["event"], optional: [...COMMON_OPTIONAL] }],
  ["interview.review.completed", { required: ["event"], optional: [...COMMON_OPTIONAL] }],
  ["resume-knowledge.resume-ingested", { required: ["event"], optional: [...COMMON_OPTIONAL] }],
  ["resume-knowledge.claim-confirmed", { required: ["event"], optional: [...COMMON_OPTIONAL] }],
  ["resume-knowledge.claim-rejected", { required: ["event"], optional: [...COMMON_OPTIONAL] }],
  ["resume-knowledge.question-bank-created", { required: ["event"], optional: [...COMMON_OPTIONAL] }],
  ["resume-knowledge.daily-plan-created", { required: ["event"], optional: [...COMMON_OPTIONAL] }],
  ["resume-knowledge.answer-scored", { required: ["event"], optional: [...COMMON_OPTIONAL] }]
]);
const namespaceFor = (eventType) => eventType.split(".")[0];

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const SESSION_ID = /^(MOCK|REAL)-[^/\\]+$/;
const RFC3339 = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;
const SESSION_FIELDS = new Set([
  "schemaVersion", "eventId", "eventKey", "eventType", "userId", "username", "sessionId",
  "interviewType", "domain", "startedAt", "completedAt", "status", "resumeContext", "questions"
]);
const QUESTION_FIELDS = new Set([
  "questionId", "domain", "sourceTags", "topicTags", "resumeClaimIds", "weaknessId",
  "question", "originalQuestion", "originalAnswer", "followUps", "timeline"
]);
const REVIEW_FIELDS = new Set([
  "schemaVersion", "eventId", "eventKey", "eventType", "userId", "username", "sessionId",
  "interviewType", "domain", "completedAt", "reviewVersion", "sourceSessionEventId", "sourceType",
  "evidenceType", "evidenceConfidence", "questionReviews", "profileChanges", "recommendations",
  "applyProfileChanges"
]);
const QUESTION_REVIEW_FIELDS = new Set(["questionId", "assessment", "evidence", "recommendations"]);
const PROFILE_CHANGE_FIELDS = new Set([
  "kind", "outcome", "domain", "weaknessId", "variantId", "competencyId", "title", "evidenceRefs"
]);
const ALGORITHM_FIELDS = new Set([
  "schemaVersion", "eventId", "eventKey", "eventType", "userId", "username", "observedAt", "source",
  "topic", "problem", "evidence", "outcome", "tags", "confidence"
]);
const ALGORITHM_PLAN_FIELDS = new Set([
  "schemaVersion", "eventId", "eventKey", "eventType", "userId", "username",
  "localDate", "planId", "timezone", "generatedAt", "items"
]);
const LOCAL_DATE = /^\d{4}-\d{2}-\d{2}$/;
const SAFE_ID = /^[0-9a-z-]+$/i;

const isObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const hasExactFields = (value, fields) => isObject(value) && Object.keys(value).every((field) => fields.has(field));
const nonEmptyString = (value) => typeof value === "string" && value.trim().length > 0;
const uuid = (value) => typeof value === "string" && UUID.test(value);
const timestamp = (value) => typeof value === "string" && RFC3339.test(value) && !Number.isNaN(Date.parse(value));
const stringArray = (value) => Array.isArray(value) && value.every((item) => typeof item === "string");

function validateQuestion(question) {
  if (!hasExactFields(question, QUESTION_FIELDS)
    || !nonEmptyString(question.questionId) || !nonEmptyString(question.domain)
    || !stringArray(question.sourceTags) || !stringArray(question.topicTags)
    || (question.resumeClaimIds !== undefined && !stringArray(question.resumeClaimIds))
    || (question.weaknessId !== undefined && question.weaknessId !== null && !nonEmptyString(question.weaknessId))
    || !nonEmptyString(question.originalQuestion) || typeof question.originalAnswer !== "string"
    || !Array.isArray(question.followUps) || !question.followUps.every(isObject)
    || !Array.isArray(question.timeline) || !question.timeline.every(isObject)) {
    throw new ProtocolError("invalid_event");
  }
}

function validateSessionEvent(event) {
  if (!hasExactFields(event, SESSION_FIELDS)
    || event.schemaVersion !== SCHEMA_VERSION || event.eventType !== "interview.session.completed"
    || !uuid(event.eventId) || !nonEmptyString(event.eventKey) || !uuid(event.userId)
    || !nonEmptyString(event.username) || !nonEmptyString(event.sessionId) || !SESSION_ID.test(event.sessionId)
    || !["mock", "real"].includes(event.interviewType)
    || ((event.sessionId.startsWith("MOCK-") ? "mock" : "real") !== event.interviewType)
    || !nonEmptyString(event.domain) || !timestamp(event.startedAt) || !timestamp(event.completedAt)
    || event.status !== "review_pending" || !isObject(event.resumeContext)
    || Object.keys(event.resumeContext).some((field) => !["used", "source", "claims"].includes(field))
    || typeof event.resumeContext.used !== "boolean" || !nonEmptyString(event.resumeContext.source)
    || !stringArray(event.resumeContext.claims) || !Array.isArray(event.questions)) {
    throw new ProtocolError("invalid_event");
  }
  event.questions.forEach(validateQuestion);
}

function validateQuestionReview(item) {
  if (!hasExactFields(item, QUESTION_REVIEW_FIELDS) || !nonEmptyString(item.questionId)
    || typeof item.assessment !== "string" || !isObject(item.evidence)
    || !Array.isArray(item.recommendations) || !item.recommendations.every(nonEmptyString)) {
    throw new ProtocolError("invalid_event");
  }
}

function validateProfileChange(item) {
  if (!hasExactFields(item, PROFILE_CHANGE_FIELDS) || !nonEmptyString(item.kind)
    || !["failed", "passed", "observed", "improving", "closed"].includes(item.outcome)) {
    throw new ProtocolError("invalid_event");
  }
  for (const field of ["domain", "weaknessId", "variantId", "competencyId", "title"]) {
    if (item[field] !== undefined && typeof item[field] !== "string") throw new ProtocolError("invalid_event");
  }
  if (item.evidenceRefs !== undefined && !stringArray(item.evidenceRefs)) throw new ProtocolError("invalid_event");
}

function validateReviewEvent(event) {
  if (!hasExactFields(event, REVIEW_FIELDS)
    || event.schemaVersion !== SCHEMA_VERSION || event.eventType !== "interview.review.completed"
    || !uuid(event.eventId) || !nonEmptyString(event.eventKey) || !uuid(event.userId)
    || !nonEmptyString(event.username) || !SESSION_ID.test(event.sessionId)
    || !["mock", "real"].includes(event.interviewType) || !nonEmptyString(event.domain)
    || !timestamp(event.completedAt) || !Number.isInteger(event.reviewVersion) || event.reviewVersion < 1
    || !uuid(event.sourceSessionEventId) || !["mock", "real"].includes(event.sourceType)
    || event.sourceType !== event.interviewType
    || !["full_transcript", "partial_transcript", "user_recall", "structured_notes", "live_notes"].includes(event.evidenceType)
    || !["high", "medium", "low"].includes(event.evidenceConfidence)
    || !Array.isArray(event.questionReviews) || !Array.isArray(event.profileChanges)
    || !Array.isArray(event.recommendations) || !event.recommendations.every(nonEmptyString)
    || typeof event.applyProfileChanges !== "boolean") {
    throw new ProtocolError("invalid_event");
  }
  event.questionReviews.forEach(validateQuestionReview);
  event.profileChanges.forEach(validateProfileChange);
}

function validateAlgorithmEvent(event) {
  if (!hasExactFields(event, ALGORITHM_FIELDS)
    || event.schemaVersion !== SCHEMA_VERSION || event.eventType !== "algorithm.learning.completed"
    || !uuid(event.eventId) || !nonEmptyString(event.eventKey) || !uuid(event.userId)
    || !nonEmptyString(event.username) || !timestamp(event.observedAt) || !nonEmptyString(event.source)
    || !nonEmptyString(event.topic) || !isObject(event.problem) || !nonEmptyString(event.problem.title)
    || !nonEmptyString(event.problem.source) || typeof event.problem.url !== "string"
    || !nonEmptyString(event.evidence) || !["incorrect", "stuck", "partial", "completed", "correct", "consulted"].includes(event.outcome)
    || !stringArray(event.tags) || !["high", "medium", "low"].includes(event.confidence)) {
    throw new ProtocolError("invalid_event");
  }
}

function validateAlgorithmPlanEvent(event) {
  if (!hasExactFields(event, ALGORITHM_PLAN_FIELDS)
    || event.schemaVersion !== SCHEMA_VERSION || event.eventType !== "algorithm.daily-plan-created"
    || !uuid(event.eventId) || !nonEmptyString(event.eventKey) || !uuid(event.userId)
    || !nonEmptyString(event.username) || !LOCAL_DATE.test(event.localDate)
    || !nonEmptyString(event.planId) || !SAFE_ID.test(event.planId)
    || !nonEmptyString(event.timezone) || !timestamp(event.generatedAt)
    || !Array.isArray(event.items) || !event.items.every(isObject)) {
    throw new ProtocolError("invalid_event");
  }
}

export function validateEventForBoundary(event, eventType) {
  if (eventType === "interview.session.completed") validateSessionEvent(event);
  else if (eventType === "interview.review.completed") validateReviewEvent(event);
  else if (eventType === "algorithm.learning.completed") validateAlgorithmEvent(event);
  else if (eventType === "algorithm.daily-plan-created") validateAlgorithmPlanEvent(event);
  else throw new ProtocolError("invalid_event_type");
}

export class ProtocolError extends Error {
  constructor(status, message = status) {
    super(message);
    this.status = status;
  }
}

export function inspectEnvelope(input) {
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
  if (namespaceFor(input.eventType) !== input.namespace) {
    throw new ProtocolError("invalid_event_type");
  }
  if (typeof input.requestId !== "string" || !input.requestId.trim()) {
    throw new ProtocolError("invalid_request_id");
  }
  if (input.identity !== undefined && (input.identity === null || Array.isArray(input.identity)
    || typeof input.identity !== "object"
    || Object.keys(input.identity).some((field) => !IDENTITY_FIELDS.has(field))
    || !nonEmptyString(input.identity.username)
    || (input.identity.userId !== undefined && !uuid(input.identity.userId)))) {
    throw new ProtocolError("invalid_identity");
  }
  if (input.payload !== undefined && (input.payload === null || Array.isArray(input.payload) || typeof input.payload !== "object")) {
    throw new ProtocolError("invalid_payload");
  }
  const schema = PAYLOAD_SCHEMA.get(input.eventType);
  if (!schema) throw new ProtocolError("invalid_event_type");
  const payload = input.payload ?? {};
  const allowed = new Set([...schema.required, ...schema.optional]);
  if (Object.keys(payload).some((field) => !allowed.has(field))
    || schema.required.some((field) => payload[field] === undefined)) {
    throw new ProtocolError("invalid_payload");
  }
  if (payload.userId !== undefined && !uuid(payload.userId)) throw new ProtocolError("invalid_payload");
  if (payload.username !== undefined && !nonEmptyString(payload.username)) throw new ProtocolError("invalid_payload");
  if (input.eventType === "system.user-registered" && !nonEmptyString(payload.displayName)) throw new ProtocolError("invalid_payload");
  if (input.eventType === "system.legacy-migration-requested" && !LEGACY_MODES.has(payload.mode)) throw new ProtocolError("invalid_payload");
  if (input.eventType === "interview.session.load" && !SESSION_ID.test(payload.sessionId)) throw new ProtocolError("invalid_payload");
  return structuredClone(input);
}

export function hasEventPayload(eventType) {
  return Boolean(PAYLOAD_SCHEMA.get(eventType)?.required.includes("event"));
}

export function validateEnvelope(input) {
  const envelope = inspectEnvelope(input);
  if (hasEventPayload(envelope.eventType)) {
    validateEventForBoundary(envelope.payload.event, envelope.eventType);
  }
  return envelope;
}
