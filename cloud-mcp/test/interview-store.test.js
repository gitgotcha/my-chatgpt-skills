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
    { ...session, eventId: "10000000-0000-4000-8000-000000000005", eventKey: "review-invalid", eventType: "interview.review.completed", sessionId: "REAL-2", reviewVersion: "1" }
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
