"""Deterministic construction of schema-1.2 mock-interview events.

The conversational skill owns the interview itself.  This module only seals
the verified identity, preserves the original question evidence, and writes a
portable local JSON copy after the single ``submit_event`` call.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any


SCHEMA_VERSION = "1.2"
_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_SESSION_ID = re.compile(r"^(?:MOCK|REAL)-[^/\\]+$")


class HandoffValidationError(ValueError):
    """Raised when an event is not safe to submit or persist locally."""


def _assert_verified_identity(identity: dict[str, object]) -> None:
    if not isinstance(identity, dict) or identity.get("verified") is not True:
        raise HandoffValidationError("verified identity is required")
    user_id = identity.get("userId")
    username = identity.get("username")
    if not isinstance(user_id, str) or not _UUID.fullmatch(user_id):
        raise HandoffValidationError("verified identity requires a UUID userId")
    if not isinstance(username, str) or not username.strip():
        raise HandoffValidationError("verified identity requires a username")


def _assert_timestamp(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise HandoffValidationError(f"{field} must be an ISO-8601 string")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HandoffValidationError(f"{field} must be an ISO-8601 string") from exc


def _selected_domain(questions: list[dict[str, object]]) -> str:
    domains = list(dict.fromkeys(
        str(question.get("domain", "")).strip()
        for question in questions
        if str(question.get("domain", "")).strip()
    ))
    return domains[0] if len(domains) == 1 else "java-backend"


def _normalize_questions(questions: list[dict[str, object]]) -> list[dict[str, object]]:
    if not isinstance(questions, list):
        raise HandoffValidationError("questions must be a list")
    normalized: list[dict[str, object]] = []
    weakness_retests = 0
    for question in questions:
        if not isinstance(question, dict):
            raise HandoffValidationError("each question must be an object")
        required = {
            "questionId", "domain", "sourceTags", "topicTags",
            "originalQuestion", "originalAnswer", "followUps", "timeline",
        }
        if not required.issubset(question):
            missing = ", ".join(sorted(required - set(question)))
            raise HandoffValidationError(f"question missing: {missing}")
        if not isinstance(question["questionId"], str) or not question["questionId"].strip():
            raise HandoffValidationError("questionId must be a non-empty string")
        if not isinstance(question["domain"], str) or not question["domain"].strip():
            raise HandoffValidationError("question domain must be a non-empty string")
        if not isinstance(question["sourceTags"], list) or not all(isinstance(tag, str) for tag in question["sourceTags"]):
            raise HandoffValidationError("sourceTags must be a list of strings")
        if not isinstance(question["topicTags"], list) or not all(isinstance(tag, str) for tag in question["topicTags"]):
            raise HandoffValidationError("topicTags must be a list of strings")
        if not isinstance(question["originalQuestion"], str) or not question["originalQuestion"].strip():
            raise HandoffValidationError("originalQuestion must be a non-empty string")
        if not isinstance(question["originalAnswer"], str):
            raise HandoffValidationError("originalAnswer must be a string")
        if not isinstance(question["followUps"], list) or not all(isinstance(item, dict) for item in question["followUps"]):
            raise HandoffValidationError("followUps must be a list of objects")
        if not isinstance(question["timeline"], list) or not all(isinstance(item, dict) for item in question["timeline"]):
            raise HandoffValidationError("timeline must be a list of objects")
        tags = {tag.lower() for tag in question["sourceTags"]}
        if tags.intersection({"profileweakness", "profile_weakness", "weakness", "historyweakness"}):
            weakness_retests += 1
        normalized.append(deepcopy(question))
    if normalized and weakness_retests / len(normalized) > 0.4:
        raise HandoffValidationError("weakness retests cannot exceed 40% of the session")
    return normalized


def create_mock_session_event(
    identity: dict[str, object],
    questions: list[dict[str, object]],
    *,
    started_at: str,
    completed_at: str,
    event_id: str,
    session_id: str,
) -> dict[str, object]:
    """Create an immutable ``interview.session.completed`` event.

    ``identity`` must be the result of the current conversation's explicit
    identity verification.  Answers, follow-up turns, and timelines are copied
    verbatim so later review never needs a transcript artifact.
    """
    _assert_verified_identity(identity)
    if not isinstance(event_id, str) or not _UUID.fullmatch(event_id):
        raise HandoffValidationError("eventId must be a UUID")
    if not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id):
        raise HandoffValidationError("sessionId must use MOCK-/REAL- and contain no path separators")
    _assert_timestamp(started_at, "startedAt")
    _assert_timestamp(completed_at, "completedAt")
    normalized_questions = _normalize_questions(questions)
    user_id = str(identity["userId"])
    username = str(identity["username"]).strip()
    return {
        "schemaVersion": SCHEMA_VERSION,
        "eventId": event_id,
        "eventKey": f"{user_id}:interview:session:{session_id}:v1",
        "eventType": "interview.session.completed",
        "userId": user_id,
        "username": username,
        "sessionId": session_id,
        "interviewType": "mock",
        "domain": _selected_domain(normalized_questions),
        "startedAt": started_at,
        "completedAt": completed_at,
        "status": "review_pending",
        "resumeContext": {"used": False, "source": "current_conversation", "claims": []},
        "questions": normalized_questions,
    }


def save_session_copy(
    event: dict[str, object],
    output_root: str | Path,
    persistence_status: str,
    drive_receipt: dict[str, object] | None = None,
) -> Path:
    """Write the portable session copy below ``outputs/interview/<userId>``."""
    if not isinstance(event, dict) or event.get("schemaVersion") != SCHEMA_VERSION:
        raise HandoffValidationError("session event must use schemaVersion 1.2")
    user_id = event.get("userId")
    session_id = event.get("sessionId")
    if not isinstance(user_id, str) or not _UUID.fullmatch(user_id):
        raise HandoffValidationError("session event requires a UUID userId")
    if not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id):
        raise HandoffValidationError("session event requires a safe sessionId")
    if persistence_status not in {"ok", "cloud_persistence_pending"}:
        raise HandoffValidationError("persistenceStatus must be ok or cloud_persistence_pending")
    destination = Path(output_root) / "interview" / user_id
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"interview-{session_id}-session.json"
    payload: dict[str, Any] = deepcopy(event)
    payload["persistenceStatus"] = persistence_status
    if drive_receipt is not None:
        payload["driveReceipt"] = deepcopy(drive_receipt)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
