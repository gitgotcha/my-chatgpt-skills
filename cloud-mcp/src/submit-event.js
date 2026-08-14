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
  const interviewStore = createInterviewStore({
    eventStore: createEventStore({ namespaceStore: namespaceStore("interview"), drive })
  });
  const identity = (payload) => ({ userId: payload.userId, username: payload.username });
  const handlers = {
    "identity.list": (_env, { namespace }) => namespaceStore(namespace).listIdentities(),
    "identity.create": (_env, { namespace, payload }) => namespaceStore(namespace).createIdentity(payload),
    "identity.verify": (_env, { namespace, payload }) => namespaceStore(namespace).verifyIdentity(payload),
    "interview.session.list": (_env, { payload }) => interviewStore.listSessions(identity(payload)),
    "interview.session.load": (_env, { payload }) => interviewStore.loadSession(identity(payload), payload.sessionId),
    "interview.session.completed": (_env, { payload }) => interviewStore.submitSession(identity(payload), payload.event),
    "interview.review.completed": (_env, { payload }) => interviewStore.submitReview(identity(payload), payload.event)
  };
  const handler = deps.handlers?.[envelope.eventType] ?? handlers[envelope.eventType];
  if (typeof handler !== "function") {
    throw new ProtocolError("invalid_event_type");
  }
  return handler(env, envelope, deps);
}
