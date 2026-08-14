import { ProtocolError, validateEnvelope } from "./protocol.js";
import { createDriveRepository } from "./google-drive.js";
import { createEventStore } from "./event-store.js";
import { createInterviewStore } from "./interview-store.js";
import { createNamespaceStore } from "./namespace-store.js";

export async function dispatchSubmitEvent(env, args, deps) {
  const envelope = validateEnvelope(args);
  const drive = deps.drive ?? createDriveRepository(env, deps);
  const stores = new Map();
  const namespaceStore = (namespace) => {
    if (!stores.has(namespace)) stores.set(namespace, deps.namespaceStores?.[namespace] ?? createNamespaceStore({ namespace, drive }));
    return stores.get(namespace);
  };
  const eventStores = new Map();
  const eventStore = (namespace) => {
    if (!eventStores.has(namespace)) {
      eventStores.set(namespace, createEventStore({ namespace, namespaceStore: namespaceStore(namespace), drive }));
    }
    return eventStores.get(namespace);
  };
  const interviewStore = () => createInterviewStore({ eventStore: eventStore("interview"), drive });
  const identity = (payload) => ({ userId: payload.userId, username: payload.username });
  const handlers = {
    "identity.list": (_env, { namespace }) => namespaceStore(namespace).listIdentities(),
    "identity.create": (_env, { namespace, payload }) => namespaceStore(namespace).createIdentity(payload),
    "identity.verify": (_env, { namespace, payload }) => namespaceStore(namespace).verifyIdentity(payload),
    "interview.session.list": async (_env, { payload }) => ({
      status: "ok",
      data: { sessions: await interviewStore().listSessions(identity(payload)) }
    }),
    "interview.session.load": async (_env, { payload }) => ({
      status: "ok",
      data: await interviewStore().loadSession(identity(payload), payload.sessionId)
    }),
    "interview.session.completed": async (_env, { payload }) => {
      const result = await interviewStore().submitSession(identity(payload), payload.event);
      return { status: "ok", ...result };
    },
    "interview.review.completed": (_env, { payload }) => interviewStore().submitReview(identity(payload), payload.event),
    "algorithm.learning.completed": (_env, { namespace, identity: boundIdentity, payload }) => {
      if (!payload?.event || payload.event.eventType !== "algorithm.learning.completed") throw new ProtocolError("invalid_event");
      return eventStore(namespace).appendEvent(boundIdentity, payload.event).then(({ event, receipt }) => ({ status: "ok", event, receipt }));
    }
  };
  const handler = deps.handlers?.[envelope.eventType] ?? handlers[envelope.eventType];
  if (typeof handler !== "function") {
    throw new ProtocolError("invalid_event_type");
  }
  return handler(env, envelope, deps);
}
