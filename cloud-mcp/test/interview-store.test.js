import assert from "node:assert/strict";
import test from "node:test";
import { createInterviewStore } from "../src/interview-store.js";

const identity = { userId: "00000000-0000-4000-8000-000000000001", username: "Ada" };
const otherIdentity = { userId: "00000000-0000-4000-8000-000000000002", username: "Grace" };
const session = {
  schemaVersion: "1.2", eventId: "10000000-0000-4000-8000-000000000001", eventKey: "session-MOCK-1-completed",
  eventType: "interview.session.completed", userId: identity.userId, username: identity.username,
  sessionId: "MOCK-1", interviewType: "mock", domain: "algorithms", completedAt: "2026-08-14T10:00:00.000Z"
};

function setup() {
  const events = [session,
    { ...session, eventId: "10000000-0000-4000-8000-000000000002", eventKey: "review-10", eventType: "interview.review.completed", reviewVersion: 10 },
    { ...session, eventId: "10000000-0000-4000-8000-000000000003", eventKey: "review-2", eventType: "interview.review.completed", reviewVersion: 2 },
    { ...session, eventId: "10000000-0000-4000-8000-000000000004", eventKey: "session-REAL-2-completed", sessionId: "REAL-2" },
    { ...session, eventId: "10000000-0000-4000-8000-000000000005", eventKey: "review-invalid", eventType: "interview.review.completed", sessionId: "REAL-2", reviewVersion: "1" },
    { ...session, eventId: "10000000-0000-4000-8000-000000000006", eventKey: "session-invalid", sessionId: "../x" }
  ];
  const eventStore = {
    appendEvent: async (_requestedIdentity, value) => ({ event: value }),
    listVerifiedEvents: async (requestedIdentity) => requestedIdentity.userId === identity.userId ? structuredClone(events) : []
  };
  return createInterviewStore({ eventStore });
}

test("one user cannot load another user's session", async () => {
  await assert.rejects(() => setup().loadSession(otherIdentity, session.sessionId), /not_found/);
});

test("listSessions exposes only summary fields and review presence", async () => {
  const sessions = await setup().listSessions(identity);
  assert.deepEqual(sessions, [
    { sessionId: "MOCK-1", interviewType: "mock", domain: "algorithms", completedAt: "2026-08-14T10:00:00.000Z", hasReview: true },
    { sessionId: "REAL-2", interviewType: "mock", domain: "algorithms", completedAt: "2026-08-14T10:00:00.000Z", hasReview: false }
  ]);
});

test("loadSession returns review versions in numeric order", async () => {
  const loaded = await setup().loadSession(identity, "MOCK-1");
  assert.deepEqual(loaded.reviews.map((review) => review.reviewVersion), [2, 10]);
});

test("loadSession rejects malformed session ids", async () => {
  await assert.rejects(() => setup().loadSession(identity, "session-1"), /invalid_session_id/);
});

test("submitSession rejects path-like session identifiers", async () => {
  await assert.rejects(() => setup().submitSession(identity, { ...session, sessionId: "../x" }), /invalid_session_id/);
});

test("submitReview preserves the verified receipt when snapshot creation fails", async () => {
  const reviewEvent = {
    ...session,
    eventId: "10000000-0000-4000-8000-000000000010",
    eventKey: `${identity.userId}:interview:review:MOCK-1:v1`,
    eventType: "interview.review.completed",
    reviewVersion: 1,
    sourceSessionEventId: session.eventId,
    applyProfileChanges: true,
    profileChanges: []
  };
  const eventStore = {
    appendEvent: async (_requestedIdentity, value) => ({ event: value, receipt: { fileId: "review-file", eventKey: value.eventKey, eventId: value.eventId } }),
    listVerifiedEvents: async () => [session, reviewEvent]
  };
  const result = await createInterviewStore({ eventStore }).submitReview(identity, reviewEvent, {
    createSnapshot: async () => { throw new Error("Drive unavailable"); }
  });
  assert.equal(result.status, "profile_cache_pending");
  assert.equal(result.receipt.eventKey, reviewEvent.eventKey);
});

test("submitReview reuses the verified event set for profile rebuild", async () => {
  let listCalls = 0;
  const reviewEvent = {
    ...session,
    eventId: "10000000-0000-4000-8000-000000000012",
    eventKey: `${identity.userId}:interview:review:MOCK-1:v1`,
    eventType: "interview.review.completed",
    reviewVersion: 1,
    sourceSessionEventId: session.eventId,
    applyProfileChanges: true,
    profileChanges: []
  };
  const eventStore = {
    appendEvent: async (_requestedIdentity, value) => ({ event: value, receipt: { fileId: "review-file", eventKey: value.eventKey, eventId: value.eventId } }),
    listVerifiedEvents: async () => { listCalls += 1; return [session]; }
  };
  const result = await createInterviewStore({ eventStore }).submitReview(identity, reviewEvent, {
    createSnapshot: async (profile) => ({ profile })
  });
  assert.equal(result.status, "ok");
  assert.equal(listCalls, 1);
  assert.equal(result.data.profile.headEventId, reviewEvent.eventId);
});

test("submitReview requires a versioned event key matching reviewVersion", async () => {
  const eventStore = {
    appendEvent: async (_requestedIdentity, value) => ({ event: value, receipt: { fileId: "review-file", eventKey: value.eventKey, eventId: value.eventId } }),
    listVerifiedEvents: async () => [session]
  };
  const store = createInterviewStore({ eventStore });
  const base = {
    ...session, eventId: "10000000-0000-4000-8000-000000000011", eventType: "interview.review.completed",
    reviewVersion: 1, sourceSessionEventId: session.eventId, applyProfileChanges: true, profileChanges: []
  };
  await assert.rejects(() => store.submitReview(identity, { ...base, eventKey: "review-without-version" }), /invalid_review_version/);
  await assert.rejects(() => store.submitReview(identity, { ...base, eventKey: "review:v2" }), /invalid_review_version/);
});
