"""Candidate-locked mock-session creation and review handoff sealing."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256


class HandoffValidationError(ValueError):
    """Raised when an unconfirmed or inconsistent mock artifact is supplied."""


def _assert_context(context: dict[str, object]) -> None:
    required = {
        "candidate_id", "display_name", "confirmed_by_user", "confirmed_at",
        "active_resume_id", "selected_domain",
    }
    if not required.issubset(context) or context.get("confirmed_by_user") is not True:
        raise HandoffValidationError("a complete explicitly confirmed context is required")
    candidate_id = context.get("candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id.startswith(("CAND-", "TEST-")):
        raise HandoffValidationError("candidate_id must be stable and confirmed")


def lock_resume(context: dict[str, object], resume_id: str | None) -> dict[str, object]:
    """Return a new confirmed context with one resume version locked for the session."""
    _assert_context(context)
    if resume_id is not None and not resume_id.startswith("RES-"):
        raise HandoffValidationError("resume_id must use the RES- prefix")
    locked = deepcopy(context)
    locked["active_resume_id"] = resume_id
    return locked


def _selected_domain(context: dict[str, object]) -> str:
    selected = context.get("selected_domain")
    if isinstance(selected, str) and selected:
        return selected
    detected = list(dict.fromkeys(context.get("detected_domains", [])))
    if len(detected) > 1:
        raise HandoffValidationError("mixed domains require an explicit user selection")
    return detected[0] if detected else "java_backend"


def create_mock_session(context: dict[str, object], questions: list[dict[str, object]]) -> dict[str, object]:
    """Create a sealed-in-intent mock session, never a review or profile event."""
    _assert_context(context)
    selected_domain = _selected_domain(context)
    retest_count = 0
    covered_topics: set[str] = set()
    weakness_ids: set[str] = set()
    normalized_questions: list[dict[str, object]] = []
    for question in questions:
        required = {"question_id", "domain", "source_tags", "topic_tags"}
        if not required.issubset(question):
            raise HandoffValidationError("each question must have shared question metadata")
        normalized = deepcopy(question)
        tags = normalized["source_tags"]
        if not isinstance(tags, list):
            raise HandoffValidationError("source_tags must be a list")
        if "profile_weakness" in tags:
            retest_count += 1
        covered_topics.update(str(topic) for topic in normalized["topic_tags"])
        weakness_ids.update(str(item) for item in normalized.get("retest_weakness_ids", []))
        normalized_questions.append(normalized)
    if questions and retest_count / len(questions) > 0.4:
        raise HandoffValidationError("weakness retests cannot exceed 40% of the session")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return {
        "schema_version": "1.0",
        "session_id": f"MOCK-{timestamp}-001",
        "candidate_id": context["candidate_id"],
        "source_type": "mock_interview",
        "evidence_type": "system_transcript",
        "evidence_confidence": 0.6,
        "selected_domain": selected_domain,
        "active_resume_id": context["active_resume_id"],
        "questions": normalized_questions,
        "covered_topics": sorted(covered_topics),
        "retest_weakness_ids": sorted(weakness_ids),
        "state": "review_pending",
    }


def seal_review_handoff(
    context: dict[str, object], session: dict[str, object], transcript: str
) -> dict[str, object]:
    """Seal immutable evidence for reviewing; no review or profile update happens here."""
    _assert_context(context)
    if session.get("candidate_id") != context["candidate_id"]:
        raise HandoffValidationError("session candidate does not match locked context")
    if session.get("source_type") != "mock_interview" or session.get("state") != "review_pending":
        raise HandoffValidationError("only pending mock sessions may be handed off")
    handoff = deepcopy(session)
    handoff["transcript_sha256"] = sha256(transcript.encode("utf-8")).hexdigest()
    handoff["handoff_target"] = "reviewing-java-backend-interviews"
    return handoff
