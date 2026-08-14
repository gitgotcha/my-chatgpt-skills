const SESSION_ID = /^(MOCK|REAL)-.+$/;

export function createInterviewStore({ eventStore }) {
  if (!eventStore?.appendEvent || !eventStore?.listVerifiedEvents) throw new Error("invalid_interview_store");

  async function events(identity) {
    return eventStore.listVerifiedEvents(identity);
  }

  async function listSessions(identity) {
    const verified = await events(identity);
    const reviews = new Set(verified.filter((event) => event.eventType === "interview.review.completed" && typeof event.sessionId === "string"
      && Number.isInteger(event.reviewVersion) && event.reviewVersion > 0).map((event) => event.sessionId));
    const sessionIds = new Set();
    return verified.filter((event) => event.eventType === "interview.session.completed" && typeof event.sessionId === "string" && !sessionIds.has(event.sessionId) && sessionIds.add(event.sessionId))
      .map((event) => ({ sessionId: event.sessionId, interviewType: event.interviewType, domain: event.domain, completedAt: event.completedAt, hasReview: reviews.has(event.sessionId) }));
  }

  async function loadSession(identity, sessionId) {
    if (typeof sessionId !== "string" || !SESSION_ID.test(sessionId)) throw new Error("invalid_session_id");
    const verified = await events(identity);
    const session = verified.find((event) => event.eventType === "interview.session.completed" && event.sessionId === sessionId);
    if (!session) throw new Error("not_found");
    const reviews = verified.filter((event) => event.eventType === "interview.review.completed" && event.sessionId === sessionId
      && Number.isInteger(event.reviewVersion) && event.reviewVersion > 0)
      .sort((left, right) => left.reviewVersion - right.reviewVersion);
    return { session, reviews };
  }

  return { submitSession: (identity, event) => eventStore.appendEvent(identity, event), listSessions, loadSession };
}
