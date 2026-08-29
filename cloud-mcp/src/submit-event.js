import { ProtocolError, inspectEnvelope, validateEventForBoundary, hasEventPayload } from "./protocol.js";
import { createDriveRepository } from "./google-drive.js";
import { createStorageLayout } from "./storage-layout.js";
import { createUserStore } from "./user-store.js";
import { createEventStore } from "./event-store.js";
import { createLegacyReader } from "./legacy-reader.js";
import { createInterviewStore } from "./interview-store.js";

const DOMAIN_BY_NAMESPACE = new Map([
  ["algorithm", "algorithm"],
  ["interview", "interview"],
  ["resume-knowledge", "resume-knowledge"]
]);

const toProtocolError = (cause) => {
  if (cause instanceof ProtocolError) return cause;
  const status = cause instanceof Error && cause.message ? cause.message : "invalid_event";
  return new ProtocolError(status);
};

function displayNameOf(envelope) {
  if (envelope.eventType.startsWith("system.")) return envelope.payload?.displayName;
  return envelope.identity?.username ?? envelope.payload?.username ?? envelope.payload?.event?.username;
}

async function bindIdentity(envelope, userStore) {
  const displayName = displayNameOf(envelope);
  if (typeof displayName !== "string" || !displayName.trim()) {
    throw new ProtocolError("invalid_display_name");
  }
  const preferredUserId = envelope.identity?.userId ?? envelope.payload?.userId;
  try {
    const resolved = await userStore.resolveOrCreate({ displayName, preferredUserId });
    const { userId, displayName: name, nameKey } = resolved.identity;
    return { userId, username: name, displayName: name, nameKey, verified: true };
  } catch (cause) {
    throw toProtocolError(cause);
  }
}

function withIdentity(envelope, identity) {
  const bound = structuredClone(envelope);
  bound.identity = { userId: identity.userId, username: identity.username };
  bound.payload.userId = identity.userId;
  bound.payload.username = identity.username;
  if (hasEventPayload(bound.eventType) && bound.payload.event) {
    bound.payload.event.userId = identity.userId;
    bound.payload.event.username = identity.username;
  }
  return bound;
}

export async function dispatchSubmitEvent(env, args, deps) {
  const envelope = inspectEnvelope(args);
  const drive = deps.drive ?? createDriveRepository(env, deps);
  const layout = deps.layout ?? createStorageLayout({ drive });
  const userStore = deps.userStore ?? createUserStore({ layout, drive });
  const identity = await bindIdentity(envelope, userStore);
  const bound = withIdentity(envelope, identity);

  if (hasEventPayload(bound.eventType)) {
    validateEventForBoundary(bound.payload.event, bound.eventType);
  }

  const legacyReader = deps.legacyReader ?? createLegacyReader({ drive });
  const stores = new Map();
  const eventStore = (namespace) => {
    if (!stores.has(namespace)) {
      stores.set(namespace, deps.eventStores?.[namespace]
        ?? createEventStore({ domain: namespace, userStore, layout, drive, legacyReader }));
    }
    return stores.get(namespace);
  };
  const interviewStore = () => createInterviewStore({ eventStore: eventStore("interview"), drive });

  const handlers = {
    "system.user-registered": async () => ({
      status: "ok",
      data: { registered: true, userId: identity.userId }
    }),
    "interview.session.list": async () => ({
      status: "ok",
      data: { sessions: await interviewStore().listSessions(identity) }
    }),
    "interview.session.load": async (_env, { payload }) => ({
      status: "ok",
      data: await interviewStore().loadSession(identity, payload.sessionId)
    }),
    "interview.session.completed": async (_env, { payload }) => {
      const result = await interviewStore().submitSession(identity, payload.event);
      return { status: "ok", ...result };
    },
    "interview.review.completed": (_env, { payload }) => interviewStore().submitReview(identity, payload.event),
    "algorithm.learning.completed": async (_env, { payload }) => {
      const { event, receipt } = await eventStore("algorithm").appendEvent(identity, payload.event);
      return { status: "ok", event, receipt };
    }
  };

  const handler = deps.handlers?.[bound.eventType] ?? handlers[bound.eventType];
  if (typeof handler !== "function") {
    throw new ProtocolError("invalid_event_type");
  }

  const domain = DOMAIN_BY_NAMESPACE.get(bound.namespace);
  const result = await handler(env, bound, {
    drive,
    layout,
    userStore,
    identity,
    domain,
    eventStore: domain ? eventStore(domain) : undefined
  });
  return { ...result, identity };
}
