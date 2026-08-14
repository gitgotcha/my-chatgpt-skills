import { ProtocolError, validateEnvelope } from "./protocol.js";
import { createDriveRepository } from "./google-drive.js";
import { createNamespaceStore } from "./namespace-store.js";

export async function dispatchSubmitEvent(env, args, deps) {
  const envelope = validateEnvelope(args);
  const drive = deps.drive ?? createDriveRepository(env, deps);
  const stores = new Map();
  const namespaceStore = (namespace) => {
    if (!stores.has(namespace)) stores.set(namespace, createNamespaceStore({ namespace, drive }));
    return stores.get(namespace);
  };
  const handlers = {
    "identity.list": (_env, { namespace }) => namespaceStore(namespace).listIdentities(),
    "identity.create": (_env, { namespace, payload }) => namespaceStore(namespace).createIdentity(payload),
    "identity.verify": (_env, { namespace, payload }) => namespaceStore(namespace).verifyIdentity(payload)
  };
  const handler = deps.handlers?.[envelope.eventType] ?? handlers[envelope.eventType];
  if (typeof handler !== "function") {
    throw new ProtocolError("invalid_event_type");
  }
  return handler(env, envelope, deps);
}
