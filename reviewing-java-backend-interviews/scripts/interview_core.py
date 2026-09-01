"""Deterministic validation and local persistence for interview review artifacts.

The active profile reducer lives in the Reliable Drive Sync Worker
(``services/reliable-drive-sync-worker/src/profile-model.js``).
This module only builds and validates schema-1.2 review events, writes the local report copy,
and keeps the domain/source planning helpers free of cloud assumptions.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from math import floor
from pathlib import Path
import re

REVIEW_SCHEMA_VERSION = "1.2"

_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_SESSION_ID = re.compile(r"^(?:MOCK|REAL)-[^/\\]+$")
_EVIDENCE_TYPES = {"full_transcript", "partial_transcript", "user_recall", "structured_notes", "live_notes"}
_EVIDENCE_CONFIDENCE = {"high", "medium", "low"}
_QUESTION_REVIEW_KEYS = {"questionId", "assessment", "evidence", "recommendations"}
_PROFILE_CHANGE_KEYS = {
    "kind", "outcome", "domain", "weaknessId", "variantId", "competencyId", "title", "evidenceRefs",
}


class ReviewValidationError(ValueError):
    """Raised when a schema-1.2 review event is unsafe to submit."""


def _require_identity(identity: dict[str, object]) -> tuple[str, str]:
    if not isinstance(identity, dict) or identity.get("verified") is not True:
        raise ReviewValidationError("verified identity is required")
    user_id = identity.get("userId")
    username = identity.get("username")
    if not isinstance(user_id, str) or not _UUID.fullmatch(user_id):
        raise ReviewValidationError("verified identity requires a UUID userId")
    if not isinstance(username, str) or not username.strip():
        raise ReviewValidationError("verified identity requires a username")
    return user_id, username.strip()


def _require_iso(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewValidationError(f"{field} must be an ISO-8601 string")
    # Cloud event timestamps must be unambiguous instants, never local/naive time.
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})",
        value,
    ):
        raise ReviewValidationError(f"{field} must include a timezone offset")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timezone required")
    except ValueError as error:
        raise ReviewValidationError(f"{field} must be an ISO-8601 string") from error
    return value


def _require_session(session: dict[str, object], user_id: str, username: str) -> tuple[str, str, str, list[dict[str, object]]]:
    if not isinstance(session, dict) or session.get("schemaVersion") != REVIEW_SCHEMA_VERSION:
        raise ReviewValidationError("session must use schemaVersion 1.2")
    if session.get("eventType") != "interview.session.completed":
        raise ReviewValidationError("source session must be completed")
    if session.get("userId") != user_id or str(session.get("username", "")).strip() != username:
        raise ReviewValidationError("identity does not match source session")
    session_id = session.get("sessionId")
    if not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id):
        raise ReviewValidationError("sessionId must use MOCK-/REAL- and contain no path separators")
    source_type = session.get("interviewType")
    if source_type not in {"mock", "real"}:
        raise ReviewValidationError("session interviewType must be mock or real")
    questions = session.get("questions")
    if not isinstance(questions, list) or not all(isinstance(item, dict) for item in questions):
        raise ReviewValidationError("source session questions must be a list")
    event_id = session.get("eventId")
    if not isinstance(event_id, str) or not _UUID.fullmatch(event_id):
        raise ReviewValidationError("source session eventId must be a UUID")
    domain = session.get("domain")
    if not isinstance(domain, str) or not domain.strip():
        raise ReviewValidationError("session domain must be a non-empty string")
    return session_id, source_type, domain.strip(), questions


def create_review_event(
    identity: dict[str, object],
    session: dict[str, object],
    *,
    question_reviews: list[dict[str, object]],
    profile_changes: list[dict[str, object]],
    recommendations: list[str],
    apply_profile_changes: bool | None = None,
    review_version: int,
    event_id: str,
    completed_at: str,
    evidence_type: str = "full_transcript",
    evidence_confidence: str = "high",
) -> dict[str, object]:
    """Build one immutable schema-1.2 ``interview.review.completed`` event."""
    user_id, username = _require_identity(identity)
    session_id, source_type, domain, source_questions = _require_session(session, user_id, username)
    if type(review_version) is not int or review_version < 1:
        raise ReviewValidationError("reviewVersion must be a positive integer")
    if not isinstance(event_id, str) or not _UUID.fullmatch(event_id):
        raise ReviewValidationError("eventId must be a UUID")
    _require_iso(completed_at, "completedAt")
    if evidence_type not in _EVIDENCE_TYPES:
        raise ReviewValidationError("unsupported evidenceType")
    if evidence_confidence not in _EVIDENCE_CONFIDENCE:
        raise ReviewValidationError("unsupported evidenceConfidence")
    if not isinstance(question_reviews, list) or not all(isinstance(item, dict) for item in question_reviews):
        raise ReviewValidationError("questionReviews must be a list of objects")
    source_ids = {item.get("questionId") for item in source_questions}
    seen_ids: set[object] = set()
    for item in question_reviews:
        unknown = set(item) - _QUESTION_REVIEW_KEYS
        if unknown:
            raise ReviewValidationError(f"questionReviews contain unsupported fields: {', '.join(sorted(unknown))}")
        question_id = item.get("questionId")
        if not isinstance(question_id, str) or not question_id.strip() or question_id not in source_ids:
            raise ReviewValidationError("questionReviews must reference source question IDs")
        if question_id in seen_ids:
            raise ReviewValidationError("questionReviews cannot contain duplicate question IDs")
        if not isinstance(item.get("assessment"), str):
            raise ReviewValidationError("questionReviews require assessment")
        if not isinstance(item.get("evidence"), dict):
            raise ReviewValidationError("questionReviews require evidence")
        item_recommendations = item.get("recommendations")
        if not isinstance(item_recommendations, list) or not all(
            isinstance(value, str) and value.strip() for value in item_recommendations
        ):
            raise ReviewValidationError("questionReviews require recommendations")
        seen_ids.add(question_id)
    if not isinstance(profile_changes, list) or not all(isinstance(item, dict) for item in profile_changes):
        raise ReviewValidationError("profileChanges must be a list of objects")
    valid_outcomes = {"failed", "passed", "observed", "improving", "closed"}
    for change in profile_changes:
        unknown = set(change) - _PROFILE_CHANGE_KEYS
        if unknown:
            raise ReviewValidationError(f"profileChanges contain unsupported fields: {', '.join(sorted(unknown))}")
        if not isinstance(change.get("kind"), str) or not str(change["kind"]).strip():
            raise ReviewValidationError("profileChanges require kind")
        if change.get("outcome") not in valid_outcomes:
            raise ReviewValidationError("profileChanges require a supported outcome")
        for field in ("domain", "weaknessId", "variantId", "competencyId", "title"):
            if field in change and not isinstance(change[field], str):
                raise ReviewValidationError(f"profileChanges field {field} must be a string")
        if "evidenceRefs" in change and (
            not isinstance(change["evidenceRefs"], list)
            or not all(isinstance(value, str) for value in change["evidenceRefs"])
        ):
            raise ReviewValidationError("profileChanges evidenceRefs must be a list of strings")
    if not isinstance(recommendations, list) or not all(isinstance(item, str) and item.strip() for item in recommendations):
        raise ReviewValidationError("recommendations must be a list of non-empty strings")
    if source_type == "mock":
        applies = True if apply_profile_changes is None else apply_profile_changes
        if not isinstance(applies, bool):
            raise ReviewValidationError("applyProfileChanges must be boolean")
    else:
        if not isinstance(apply_profile_changes, bool):
            raise ReviewValidationError("real review requires explicit applyProfileChanges confirmation")
        applies = apply_profile_changes
    return {
        "schemaVersion": REVIEW_SCHEMA_VERSION,
        "eventId": event_id,
        "eventKey": f"{user_id}:interview:review:{session_id}:v{review_version}",
        "eventType": "interview.review.completed",
        "userId": user_id,
        "username": username,
        "sessionId": session_id,
        "interviewType": source_type,
        "domain": domain,
        "reviewVersion": review_version,
        "sourceSessionEventId": session["eventId"],
        "sourceType": source_type,
        "evidenceType": evidence_type,
        "evidenceConfidence": evidence_confidence,
        "questionReviews": deepcopy(question_reviews),
        "profileChanges": deepcopy(profile_changes),
        "recommendations": list(recommendations),
        "applyProfileChanges": applies,
        "completedAt": completed_at,
    }


def save_review_json(
    review_event: dict[str, object],
    output_root: str | Path,
    persistence_status: str,
    outbox_receipt: dict[str, object] | None = None,
) -> Path:
    """Write a portable local report JSON; it is never a profile input."""
    if not isinstance(review_event, dict) or review_event.get("schemaVersion") != REVIEW_SCHEMA_VERSION:
        raise ReviewValidationError("review event must use schemaVersion 1.2")
    user_id = review_event.get("userId")
    session_id = review_event.get("sessionId")
    if not isinstance(user_id, str) or not _UUID.fullmatch(user_id):
        raise ReviewValidationError("review event requires a UUID userId")
    if not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id):
        raise ReviewValidationError("review event requires a safe sessionId")
    if persistence_status not in {"cloud_accepted", "pending"}:
        raise ReviewValidationError("unsupported persistenceStatus")
    destination = Path(output_root) / "interview" / user_id
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"interview-{session_id}-report.json"
    payload = deepcopy(review_event)
    payload["persistenceStatus"] = persistence_status
    if outbox_receipt is not None:
        payload["outboxReceipt"] = deepcopy(outbox_receipt)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def resolve_domain(
    explicit: str | None, resume_domains: list[str], profile_domains: list[str]
) -> str | None:
    """Resolve a domain without guessing when the strongest evidence is mixed."""
    if explicit:
        return explicit
    resume_unique = list(dict.fromkeys(resume_domains))
    if len(resume_unique) == 1:
        return resume_unique[0]
    if len(resume_unique) > 1:
        return None
    profile_unique = list(dict.fromkeys(profile_domains))
    if len(profile_unique) == 1:
        return profile_unique[0]
    if len(profile_unique) > 1:
        return None
    return "java_backend"


def _allocate(total: int, weights: dict[str, int]) -> dict[str, int]:
    if total < 0:
        raise ValueError("total_questions cannot be negative")
    total_weight = sum(weights.values())
    raw = {name: total * weight / total_weight for name, weight in weights.items()}
    allocated = {name: floor(value) for name, value in raw.items()}
    remaining = total - sum(allocated.values())
    order = sorted(weights, key=lambda name: (-(raw[name] - allocated[name]), list(weights).index(name)))
    for name in order[:remaining]:
        allocated[name] += 1
    return allocated


def plan_question_sources(has_resume: bool, total_questions: int) -> dict[str, int]:
    """Plan rounded source counts while preserving the 40% weakness ceiling."""
    if has_resume:
        return _allocate(total_questions, {
            "resume": 35,
            "profile_weakness": 30,
            "domain_knowledge": 25,
            "algorithm_and_scenario": 10,
        })
    return _allocate(total_questions, {
        "profile_weakness": 35,
        "domain_knowledge": 45,
        "algorithm_and_scenario": 20,
    })
