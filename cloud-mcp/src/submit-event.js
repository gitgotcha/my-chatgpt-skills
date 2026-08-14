import { ProtocolError, validateEnvelope } from "./protocol.js";

export async function dispatchSubmitEvent(env, args, deps) {
  const envelope = validateEnvelope(args);
  const handler = deps.handlers?.[envelope.eventType];
  if (typeof handler !== "function") {
    throw new ProtocolError("invalid_event_type");
  }
  return handler(env, envelope, deps);
}
