"""Deterministic construction of interview snapshot content.

The conversational skill owns the interview itself. This module preserves the
original question evidence and builds content for a user-readable RDS-JBryon
snapshot. It does not resolve identity, create event envelopes, or persist data.

Project contract v1 (design 2026-10-24, §5) is opt-in: legacy callers keep the
old ``MOCK-``/``REAL-`` mock shape and the 40% weakness ceiling, while
``project_contract_version=1`` accepts ``LEARN-`` project-learning sessions,
requires one ``projectEvidence`` block per question, and writes
``projectContractVersion: 1`` after a local structural check.  The Worker is
still the accepting boundary; this guard mirrors it for local safety only.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any


SCHEMA_VERSION = "interview-session-snapshot/2"
PROJECT_CONTRACT_VERSION = 1
MODES = frozenset({"full_mock", "project_targeted", "project_learning"})

_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_SESSION_ID = re.compile(r"^(?:MOCK|REAL|LEARN)-[^/\\]+$")
_PROJECT_QUESTION_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

_PROJECT_FIELDS = frozenset(
    {"projectId", "displayName", "basis", "resumeVersion", "resumeClaimIds", "sourceRevision"}
)
_PROJECT_BASIS_FIELDS = frozenset({"kind", "key"})
_PROJECT_BASIS_KINDS = frozenset({"resume_claim", "user_confirmed", "source_learning"})
_PROJECT_EVIDENCE_FIELDS = frozenset(
    {
        "project", "attemptId", "questionKey", "variantId", "variantAxes",
        "purpose", "sourceSkill", "provenance", "sourceRefs",
    }
)
_PROJECT_PROVENANCE_FIELDS = frozenset(
    {"answerOrigin", "assistance", "exactAnswerSeenBefore", "exposureGroupId"}
)
_PROJECT_ANSWER_ORIGINS = frozenset({"actual_user", "user_recall"})
_PROJECT_ASSISTANCE = frozenset({"none", "hint", "answer_shown"})
_PROJECT_PURPOSES = frozenset({"initial_assessment", "targeted_retest"})
_PROJECT_SOURCE_SKILLS = frozenset(
    {
        "software-project-learning",
        "conducting-java-backend-mock-interviews",
        "reviewing-java-backend-interviews",
    }
)


class HandoffValidationError(ValueError):
    """Raised when an event is not safe to submit or persist locally."""


def _assert_timestamp(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise HandoffValidationError(f"{field} must be an ISO-8601 string")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HandoffValidationError(f"{field} must be an ISO-8601 string") from exc


def _bounded_text(value: object, maximum: int, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise HandoffValidationError(
            f"{field} must be a non-empty string of at most {maximum} characters"
        )
    return value


def _validate_project_block(project: object) -> None:
    if not isinstance(project, dict) or set(project) != _PROJECT_FIELDS:
        raise HandoffValidationError(
            "projectEvidence.project must use exactly the project contract v1 fields"
        )
    if not (isinstance(project["projectId"], str) and _UUID.fullmatch(project["projectId"])):
        raise HandoffValidationError("projectEvidence.project.projectId must be a UUID")
    _bounded_text(project["displayName"], 200, "projectEvidence.project.displayName")

    basis = project["basis"]
    if not isinstance(basis, dict) or set(basis) != _PROJECT_BASIS_FIELDS:
        raise HandoffValidationError("projectEvidence.project.basis must contain exactly kind and key")
    if basis["kind"] not in _PROJECT_BASIS_KINDS:
        raise HandoffValidationError("projectEvidence.project.basis.kind is not supported")
    _bounded_text(basis["key"], 256, "projectEvidence.project.basis.key")

    resume_version = project["resumeVersion"]
    if resume_version is not None and not (
        isinstance(resume_version, str) and len(resume_version) <= 128
    ):
        raise HandoffValidationError("projectEvidence.project.resumeVersion must be a string or null")
    claim_ids = project["resumeClaimIds"]
    if (
        not isinstance(claim_ids, list)
        or len(claim_ids) > 50
        or not all(isinstance(item, str) for item in claim_ids)
    ):
        raise HandoffValidationError("projectEvidence.project.resumeClaimIds must be a list of strings")
    source_revision = project["sourceRevision"]
    if source_revision is not None and not (
        isinstance(source_revision, str) and len(source_revision) <= 200
    ):
        raise HandoffValidationError("projectEvidence.project.sourceRevision must be a string or null")


def _validate_provenance(provenance: object) -> None:
    if not isinstance(provenance, dict) or set(provenance) != _PROJECT_PROVENANCE_FIELDS:
        raise HandoffValidationError(
            "projectEvidence.provenance must use exactly the project contract v1 fields"
        )
    if provenance["answerOrigin"] not in _PROJECT_ANSWER_ORIGINS:
        raise HandoffValidationError("projectEvidence.provenance.answerOrigin is not supported")
    if provenance["assistance"] not in _PROJECT_ASSISTANCE:
        raise HandoffValidationError("projectEvidence.provenance.assistance is not supported")
    if not isinstance(provenance["exactAnswerSeenBefore"], bool):
        raise HandoffValidationError("projectEvidence.provenance.exactAnswerSeenBefore must be a boolean")
    _bounded_text(
        provenance["exposureGroupId"], 128, "projectEvidence.provenance.exposureGroupId"
    )


def _validate_project_evidence(evidence: object) -> None:
    if not isinstance(evidence, dict) or set(evidence) != _PROJECT_EVIDENCE_FIELDS:
        raise HandoffValidationError(
            "projectEvidence must use exactly the project contract v1 fields"
        )
    _validate_project_block(evidence["project"])
    if not (isinstance(evidence["attemptId"], str) and _UUID.fullmatch(evidence["attemptId"])):
        raise HandoffValidationError("projectEvidence.attemptId must be a UUID")
    question_key = evidence["questionKey"]
    if not isinstance(question_key, str) or not _PROJECT_QUESTION_KEY.fullmatch(question_key):
        raise HandoffValidationError("projectEvidence.questionKey is not a stable question key")
    _bounded_text(evidence["variantId"], 128, "projectEvidence.variantId")
    axes = evidence["variantAxes"]
    if (
        not isinstance(axes, list)
        or not 1 <= len(axes) <= 4
        or not all(isinstance(axis, str) and axis.strip() and len(axis) <= 64 for axis in axes)
    ):
        raise HandoffValidationError("projectEvidence.variantAxes must contain 1-4 non-empty strings")
    if evidence["purpose"] not in _PROJECT_PURPOSES:
        raise HandoffValidationError("projectEvidence.purpose is not a supported purpose")
    if evidence["sourceSkill"] not in _PROJECT_SOURCE_SKILLS:
        raise HandoffValidationError("projectEvidence.sourceSkill is not supported")
    _validate_provenance(evidence["provenance"])
    refs = evidence["sourceRefs"]
    if (
        not isinstance(refs, list)
        or not 1 <= len(refs) <= 20
        or not all(isinstance(ref, str) and ref.strip() and len(ref) <= 2048 for ref in refs)
    ):
        raise HandoffValidationError(
            "projectEvidence.sourceRefs must contain 1-20 non-empty strings"
        )


def _selected_domain(questions: list[dict[str, object]]) -> str:
    domains = list(dict.fromkeys(
        str(question.get("domain", "")).strip()
        for question in questions
        if str(question.get("domain", "")).strip()
    ))
    return domains[0] if len(domains) == 1 else "java-backend"


def _normalize_questions(
    questions: list[dict[str, object]],
    *,
    mode: str,
    project_contract_version: int | None,
    interview_type: str,
) -> list[dict[str, object]]:
    if not isinstance(questions, list):
        raise HandoffValidationError("questions must be a list")
    normalized: list[dict[str, object]] = []
    weakness_retests = 0
    project_ids: set[str] = set()
    attempt_ids: set[str] = set()
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

        evidence = question.get("projectEvidence")
        if project_contract_version is None:
            if evidence is not None:
                raise HandoffValidationError(
                    "projectEvidence requires projectContractVersion 1"
                )
        else:
            if evidence is None:
                raise HandoffValidationError(
                    "every question requires projectEvidence when projectContractVersion is 1"
                )
            _validate_project_evidence(evidence)
            project_ids.add(evidence["project"]["projectId"])
            attempt_id = evidence["attemptId"]
            if attempt_id in attempt_ids:
                raise HandoffValidationError(
                    "project attempts must be unique within a session"
                )
            attempt_ids.add(attempt_id)

        tags = {tag.lower() for tag in question["sourceTags"]}
        if tags.intersection({"profileweakness", "profile_weakness", "weakness", "historyweakness"}):
            weakness_retests += 1
        normalized.append(deepcopy(question))

    if project_contract_version == PROJECT_CONTRACT_VERSION:
        if not normalized:
            raise HandoffValidationError(
                "projectContractVersion 1 requires at least one answered question"
            )
        single_project_session = mode in {"project_targeted", "project_learning"} or (
            interview_type == "project_learning"
        )
        if single_project_session and len(project_ids) > 1:
            raise HandoffValidationError(
                "a project targeted/learning session must reference exactly one project"
            )
    # The full-mock ceiling stays exactly as before; project-targeted sessions
    # are allowed to consist entirely of the selected project's weaknesses.
    if mode == "full_mock" and normalized and weakness_retests / len(normalized) > 0.4:
        raise HandoffValidationError("weakness retests cannot exceed 40% of the session")
    return normalized


def create_mock_session_snapshot(
    questions: list[dict[str, object]],
    *,
    started_at: str,
    completed_at: str,
    session_id: str,
    mode: str = "full_mock",
    project_contract_version: int | None = None,
) -> dict[str, object]:
    """Create snapshot content while preserving answers and follow-up turns.

    ``mode`` defaults to the legacy full mock.  ``project_targeted`` and
    ``project_learning`` require ``project_contract_version=1``; a ``LEARN-``
    session id is only accepted with that contract and becomes
    ``interviewType: project_learning``.
    """
    if mode not in MODES:
        raise HandoffValidationError(
            "mode must be full_mock, project_targeted or project_learning"
        )
    if not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id):
        raise HandoffValidationError(
            "sessionId must use MOCK-/REAL-/LEARN- and contain no path separators"
        )
    if project_contract_version is not None and project_contract_version != PROJECT_CONTRACT_VERSION:
        raise HandoffValidationError("projectContractVersion must be 1")
    if project_contract_version is None:
        if mode != "full_mock":
            raise HandoffValidationError(f"{mode} requires projectContractVersion 1")
        if session_id.startswith("LEARN-"):
            raise HandoffValidationError("LEARN- sessionId requires projectContractVersion 1")
    elif mode == "project_learning" and not session_id.startswith("LEARN-"):
        raise HandoffValidationError("project_learning requires a LEARN- sessionId")

    _assert_timestamp(started_at, "startedAt")
    _assert_timestamp(completed_at, "completedAt")

    interview_type = "mock"
    if project_contract_version == PROJECT_CONTRACT_VERSION:
        if session_id.startswith("LEARN-"):
            interview_type = "project_learning"
        elif session_id.startswith("REAL-"):
            interview_type = "real"

    normalized_questions = _normalize_questions(
        questions,
        mode=mode,
        project_contract_version=project_contract_version,
        interview_type=interview_type,
    )
    snapshot: dict[str, object] = {
        "schemaVersion": SCHEMA_VERSION,
        "sessionId": session_id,
        "interviewType": interview_type,
        "domain": _selected_domain(normalized_questions),
        "startedAt": started_at,
        "completedAt": completed_at,
        "status": "review_pending",
        "resumeContext": {"used": False, "source": "current_conversation", "claims": []},
        "questions": normalized_questions,
    }
    if project_contract_version == PROJECT_CONTRACT_VERSION:
        snapshot["projectContractVersion"] = PROJECT_CONTRACT_VERSION
    return snapshot


def save_session_copy(
    snapshot: dict[str, object],
    output_root: str | Path,
) -> Path:
    """Write a local report copy; this is not evidence of an RDS save."""
    if not isinstance(snapshot, dict) or snapshot.get("schemaVersion") != SCHEMA_VERSION:
        raise HandoffValidationError("session must use the RDS-JBryon snapshot schema")
    session_id = snapshot.get("sessionId")
    if not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id):
        raise HandoffValidationError("session snapshot requires a safe sessionId")
    destination = Path(output_root) / "interview"
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"interview-{session_id}-session.json"
    payload: dict[str, Any] = deepcopy(snapshot)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
