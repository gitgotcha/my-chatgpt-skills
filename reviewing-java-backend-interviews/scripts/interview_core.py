"""Deterministic validation and local copies of interview review snapshots.

RDS-JBryon persistence is performed by the Skill through readable routes. This
module only assembles content and a local report copy; it never resolves a
person, creates an event envelope, or claims that the cloud save completed.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from math import floor
from pathlib import Path
import re

REVIEW_SCHEMA_VERSION = "interview-review-snapshot/2"

_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_SESSION_ID = re.compile(r"^(?:MOCK|REAL|LEARN)-[^/\\]+$")
_EVIDENCE_TYPES = {"full_transcript", "partial_transcript", "user_recall", "structured_notes", "live_notes"}
_EVIDENCE_CONFIDENCE = {"high", "medium", "low"}
_QUESTION_REVIEW_KEYS = {"questionId", "assessment", "evidence", "recommendations", "projectAssessment"}
_PROFILE_CHANGE_KEYS = {
    "kind", "outcome", "domain", "weaknessId", "variantId", "competencyId", "title", "evidenceRefs",
}


class ReviewValidationError(ValueError):
    """Raised when review snapshot content violates its contract."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        # Stable machine code; older call sites only pass a message, and the
        # message itself is stable there, so the default keeps their behavior.
        self.code = code or message


def _require_iso(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewValidationError(f"{field} must be an ISO-8601 string")
    # Timestamps must identify an unambiguous instant, never naive local time.
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


def _require_session(session: dict[str, object]) -> tuple[str, str, str, list[dict[str, object]]]:
    if not isinstance(session, dict) or session.get("schemaVersion") != "interview-session-snapshot/2":
        raise ReviewValidationError("source must use interview-session-snapshot/2")
    session_id = session.get("sessionId")
    if not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id):
        raise ReviewValidationError("sessionId must use MOCK-/REAL-/LEARN- and contain no path separators")
    source_type = session.get("interviewType")
    if source_type not in {"mock", "real", "project_learning"}:
        raise ReviewValidationError("session interviewType must be mock, real or project_learning")
    expected_prefix = {"mock": "MOCK-", "real": "REAL-", "project_learning": "LEARN-"}[source_type]
    if not session_id.startswith(expected_prefix):
        raise ReviewValidationError("sessionId prefix must match interviewType")
    contract_version = session.get("projectContractVersion")
    if contract_version not in (None, 1):
        raise ReviewValidationError("projectContractVersion must be 1", "project_contract_version_unsupported")
    if source_type == "project_learning" and contract_version != 1:
        raise ReviewValidationError(
            "project_learning requires projectContractVersion 1", "project_contract_version_unsupported"
        )
    questions = session.get("questions")
    if not isinstance(questions, list) or not all(isinstance(item, dict) for item in questions):
        raise ReviewValidationError("source session questions must be a list")
    domain = session.get("domain")
    if not isinstance(domain, str) or not domain.strip():
        raise ReviewValidationError("session domain must be a non-empty string")
    return session_id, source_type, domain.strip(), questions


def create_review_snapshot(
    session: dict[str, object],
    *,
    question_reviews: list[dict[str, object]],
    profile_changes: list[dict[str, object]],
    recommendations: list[str],
    apply_profile_changes: bool | None = None,
    review_version: int,
    completed_at: str,
    evidence_type: str = "full_transcript",
    evidence_confidence: str = "high",
) -> dict[str, object]:
    """Build one review record linked to a source session by its readable ID."""
    session_id, source_type, domain, source_questions = _require_session(session)
    if type(review_version) is not int or review_version < 1:
        raise ReviewValidationError("reviewVersion must be a positive integer")
    _require_iso(completed_at, "completedAt")
    if evidence_type not in _EVIDENCE_TYPES:
        raise ReviewValidationError("unsupported evidenceType")
    if evidence_confidence not in _EVIDENCE_CONFIDENCE:
        raise ReviewValidationError("unsupported evidenceConfidence")
    if not isinstance(question_reviews, list) or not all(isinstance(item, dict) for item in question_reviews):
        raise ReviewValidationError("questionReviews must be a list of objects")
    source_ids = {item.get("questionId") for item in source_questions}
    questions_by_id = {item.get("questionId"): item for item in source_questions}
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
        if "projectAssessment" in item:
            validate_project_assessment(item, questions_by_id[question_id])
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
    if session.get("projectContractVersion") == 1 and source_type == "project_learning" and profile_changes:
        raise ReviewValidationError(
            "project_learning reviews may not carry profileChanges", "invalid_project_evidence"
        )
    snapshot = {
        "schemaVersion": REVIEW_SCHEMA_VERSION,
        "sessionId": session_id,
        "interviewType": source_type,
        "domain": domain,
        "reviewVersion": review_version,
        "sourceSessionId": session_id,
        "sourceType": source_type,
        "evidenceType": evidence_type,
        "evidenceConfidence": evidence_confidence,
        "questionReviews": deepcopy(question_reviews),
        "profileChanges": deepcopy(profile_changes),
        "recommendations": list(recommendations),
        "applyProfileChanges": applies,
        "completedAt": completed_at,
    }
    if session.get("projectContractVersion") == 1:
        snapshot["projectContractVersion"] = 1
    return snapshot


def save_review_json(
    review_snapshot: dict[str, object],
    output_root: str | Path,
) -> Path:
    """Write a local report copy; it does not confirm an RDS-JBryon save."""
    if not isinstance(review_snapshot, dict) or review_snapshot.get("schemaVersion") != REVIEW_SCHEMA_VERSION:
        raise ReviewValidationError("review snapshot must use interview-review-snapshot/2")
    session_id = review_snapshot.get("sessionId")
    if not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id):
        raise ReviewValidationError("review snapshot requires a safe sessionId")
    destination = Path(output_root) / "interview"
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"interview-{session_id}-report.json"
    payload = deepcopy(review_snapshot)
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

# ---------------------------------------------------------------------------
# Project interview contract v1 (design 2026-10-24, §5).
#
# The Worker owns the accepting boundary; this mirror exists so the Python
# builders refuse exactly what the server would refuse, which keeps local
# artifacts and the cloud contract from drifting apart. Pure: no I/O.
# ---------------------------------------------------------------------------

PROJECT_CONTRACT_VERSION = 1
PROJECT_RUBRIC_VERSION = "project-campus-v1"
PROJECT_SCORE_CAPS = {
    "technical": 30,
    "projectEvidence": 25,
    "causal": 20,
    "tradeoff": 15,
    "expression": 10,
}
PROJECT_PASS_MINIMUMS = {"total": 80, "technical": 24, "projectEvidence": 18, "causal": 14}
MAX_PROJECT_ENVELOPE_BYTES = 48 * 1024
MAX_PROJECT_QUESTION_BYTES = 24 * 1024
MAX_PROJECT_ASSESSMENT_BYTES = 8 * 1024
PROJECT_BASIS_KINDS = {"resume_claim", "user_confirmed", "source_learning"}
PROJECT_PURPOSES = {"initial_assessment", "targeted_retest"}
PROJECT_ANSWER_ORIGINS = {"actual_user", "user_recall"}
PROJECT_ASSISTANCE = {"none", "hint", "answer_shown"}
PROJECT_ASSESSMENT_OUTCOMES = {"passed", "partial", "failed", "unscored"}
PROJECT_WEAKNESS_OUTCOMES = {"failed", "passed", "observed"}
PROJECT_SOURCE_SKILLS = {
    "software-project-learning",
    "conducting-java-backend-mock-interviews",
    "reviewing-java-backend-interviews",
}
_PROJECT_FIELDS = {"projectId", "displayName", "basis", "resumeVersion", "resumeClaimIds", "sourceRevision"}
_PROJECT_EVIDENCE_FIELDS = {
    "project", "attemptId", "questionKey", "variantId", "variantAxes", "purpose",
    "sourceSkill", "provenance", "sourceRefs",
}
_PROJECT_PROVENANCE_FIELDS = {"answerOrigin", "assistance", "exactAnswerSeenBefore", "exposureGroupId"}
_PROJECT_ASSESSMENT_FIELDS = {
    "attemptId", "rubricVersion", "scores", "total", "outcome", "evidenceRefs", "reason", "weaknesses",
}
_PROJECT_WEAKNESS_FIELDS = {"weaknessId", "title", "outcome"}
_PROJECT_BASIS_FIELDS = {"kind", "key"}
_QUESTION_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _project_fail(code: str, detail: str = "") -> None:
    raise ReviewValidationError(f"{code}:{detail}" if detail else code, code)


def _project_bytes(value: object) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _exact_fields(value: object, fields: set[str]) -> bool:
    return isinstance(value, dict) and set(value).issubset(fields)


def _bounded(value: object, maximum: int) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= maximum


def _validate_project_block(project: object) -> None:
    if not _exact_fields(project, _PROJECT_FIELDS):
        _project_fail("invalid_project_evidence", "project_fields")
    if not (isinstance(project["projectId"], str) and _UUID.fullmatch(project["projectId"])):
        _project_fail("invalid_project_evidence", "project_id")
    if not _bounded(project["displayName"], 200):
        _project_fail("invalid_project_evidence", "display_name")
    basis = project["basis"]
    if not _exact_fields(basis, _PROJECT_BASIS_FIELDS):
        _project_fail("invalid_project_evidence", "basis_fields")
    if basis.get("kind") not in PROJECT_BASIS_KINDS or not _bounded(basis.get("key"), 256):
        _project_fail("invalid_project_evidence", "basis")
    resume_version = project["resumeVersion"]
    if not (resume_version is None or _bounded(resume_version, 128)):
        _project_fail("invalid_project_evidence", "resume_version")
    claim_ids = project["resumeClaimIds"]
    if not isinstance(claim_ids, list) or len(claim_ids) > 50 or not all(isinstance(item, str) for item in claim_ids):
        _project_fail("invalid_project_evidence", "resume_claim_ids")
    source_revision = project["sourceRevision"]
    if not (source_revision is None or _bounded(source_revision, 200)):
        _project_fail("invalid_project_evidence", "source_revision")


def _validate_provenance(provenance: object) -> None:
    if not _exact_fields(provenance, _PROJECT_PROVENANCE_FIELDS):
        _project_fail("invalid_project_evidence", "provenance_fields")
    if provenance.get("answerOrigin") not in PROJECT_ANSWER_ORIGINS:
        _project_fail("invalid_project_evidence", "answer_origin")
    if provenance.get("assistance") not in PROJECT_ASSISTANCE:
        _project_fail("invalid_project_evidence", "assistance")
    if not isinstance(provenance.get("exactAnswerSeenBefore"), bool):
        _project_fail("invalid_project_evidence", "exact_answer_seen")
    if not _bounded(provenance.get("exposureGroupId"), 128):
        _project_fail("invalid_project_evidence", "exposure_group")


def validate_project_question(question: object) -> None:
    """Validate ``question['projectEvidence']``; raises ReviewValidationError."""
    evidence = question.get("projectEvidence") if isinstance(question, dict) else None
    if not isinstance(evidence, dict):
        _project_fail("invalid_project_evidence", "missing")
    if not _exact_fields(evidence, _PROJECT_EVIDENCE_FIELDS):
        _project_fail("invalid_project_evidence", "evidence_fields")
    _validate_project_block(evidence["project"])
    if not (isinstance(evidence["attemptId"], str) and _UUID.fullmatch(evidence["attemptId"])):
        _project_fail("invalid_project_evidence", "attempt_id")
    if not _QUESTION_KEY.fullmatch(str(evidence.get("questionKey", ""))):
        _project_fail("invalid_project_evidence", "question_key")
    if not _bounded(evidence.get("variantId"), 128):
        _project_fail("invalid_project_evidence", "variant_id")
    axes = evidence.get("variantAxes")
    if not isinstance(axes, list) or not 1 <= len(axes) <= 4 or not all(_bounded(axis, 64) for axis in axes):
        _project_fail("invalid_project_evidence", "variant_axes")
    if evidence.get("purpose") not in PROJECT_PURPOSES:
        _project_fail("invalid_project_evidence", "purpose")
    if evidence.get("sourceSkill") not in PROJECT_SOURCE_SKILLS:
        _project_fail("invalid_project_evidence", "source_skill")
    _validate_provenance(evidence["provenance"])
    refs = evidence.get("sourceRefs")
    if not isinstance(refs, list) or not 1 <= len(refs) <= 20 or not all(_bounded(ref, 2048) for ref in refs):
        _project_fail("invalid_project_evidence", "source_refs")
    if _project_bytes(evidence) > 16 * 1024:
        _project_fail("invalid_project_evidence", "too_large")


def _validate_assessment_shape(assessment: object) -> None:
    if not _exact_fields(assessment, _PROJECT_ASSESSMENT_FIELDS):
        _project_fail("invalid_project_evidence", "assessment_fields")
    if not (isinstance(assessment["attemptId"], str) and _UUID.fullmatch(assessment["attemptId"])):
        _project_fail("invalid_project_evidence", "assessment_attempt")
    if assessment.get("rubricVersion") != PROJECT_RUBRIC_VERSION:
        _project_fail("invalid_project_evidence", "rubric")
    if assessment.get("outcome") not in PROJECT_ASSESSMENT_OUTCOMES:
        _project_fail("invalid_project_evidence", "outcome")
    if not _bounded(assessment.get("reason"), 8000):
        _project_fail("invalid_project_evidence", "reason")
    weaknesses = assessment.get("weaknesses")
    if not isinstance(weaknesses, list) or len(weaknesses) > 20:
        _project_fail("invalid_project_evidence", "weaknesses")
    for weakness in weaknesses:
        if not _exact_fields(weakness, _PROJECT_WEAKNESS_FIELDS):
            _project_fail("invalid_project_evidence", "weakness_fields")
        if not _bounded(weakness.get("weaknessId"), 128) or not _bounded(weakness.get("title"), 200):
            _project_fail("invalid_project_evidence", "weakness")
        if weakness.get("outcome") not in PROJECT_WEAKNESS_OUTCOMES:
            _project_fail("invalid_project_evidence", "weakness_outcome")
    scores = assessment.get("scores")
    if scores is None:
        if assessment.get("total") is not None or assessment.get("outcome") != "unscored":
            _project_fail("invalid_project_evidence", "unscored_inconsistent")
    else:
        if not isinstance(scores, dict) or set(scores) != set(PROJECT_SCORE_CAPS):
            _project_fail("invalid_project_evidence", "scores")
        for key, cap in PROJECT_SCORE_CAPS.items():
            value = scores.get(key)
            if type(value) is not int or not 0 <= value <= cap:
                _project_fail("invalid_project_evidence", "score_range")
        total = sum(scores.values())
        if type(assessment.get("total")) is not int or assessment["total"] != total:
            _project_fail("invalid_project_evidence", "total")
        if not 0 <= total <= 100:
            _project_fail("invalid_project_evidence", "total_range")
        if assessment.get("outcome") == "unscored":
            _project_fail("invalid_project_evidence", "unscored_with_scores")
    if assessment.get("outcome") == "passed":
        if scores is None:
            _project_fail("invalid_project_evidence", "pass_threshold")
        minimums = PROJECT_PASS_MINIMUMS
        if (assessment["total"] < minimums["total"]
                or scores["technical"] < minimums["technical"]
                or scores["projectEvidence"] < minimums["projectEvidence"]
                or scores["causal"] < minimums["causal"]):
            _project_fail("invalid_project_evidence", "pass_threshold")
        if any(weakness.get("outcome") == "failed" for weakness in assessment["weaknesses"]):
            _project_fail("invalid_project_evidence", "pass_with_failed_weakness")


def _evidence_targets(question: object) -> set[str]:
    targets = {"originalAnswer"}
    timeline = question.get("timeline") if isinstance(question, dict) else None
    for entry in timeline if isinstance(timeline, list) else []:
        if isinstance(entry, dict) and isinstance(entry.get("messageId"), str) and entry["messageId"].strip():
            targets.add(f"timeline:{entry['messageId']}")
    return targets


def validate_project_assessment(review_item: object, question: object) -> None:
    """Validate one ``projectAssessment`` against its question."""
    assessment = review_item.get("projectAssessment") if isinstance(review_item, dict) else None
    if not isinstance(assessment, dict):
        _project_fail("invalid_project_evidence", "missing_assessment")
    _validate_assessment_shape(assessment)
    evidence = question.get("projectEvidence") if isinstance(question, dict) else None
    if not isinstance(evidence, dict):
        _project_fail("review_source_mismatch", "question_has_no_project_evidence")
    if assessment["attemptId"] != evidence.get("attemptId"):
        _project_fail("assessment_question_mismatch", "attempt")
    refs = assessment.get("evidenceRefs")
    if not isinstance(refs, list) or not 1 <= len(refs) <= 20:
        _project_fail("assessment_evidence_unresolvable", "missing")
    targets = _evidence_targets(question)
    prefix = f"{review_item.get('questionId')}:"
    for ref in refs:
        if not isinstance(ref, str) or not ref.strip():
            _project_fail("assessment_evidence_unresolvable", "empty")
        if not ref.startswith(prefix):
            _project_fail("assessment_evidence_unresolvable", "question_prefix")
        if ref[len(prefix):] not in targets:
            _project_fail("assessment_evidence_unresolvable", "target")
    if _project_bytes(assessment) > MAX_PROJECT_ASSESSMENT_BYTES:
        _project_fail("project_envelope_too_large", "assessment")


def validate_project_session_event(event: object) -> None:
    """Session-level rules, mirroring the Worker boundary for project v1."""
    if event.get("projectContractVersion") != PROJECT_CONTRACT_VERSION:
        _project_fail("project_contract_version_unsupported", "version")
    interview_type = event.get("interviewType")
    prefixes = {"mock": "MOCK-", "real": "REAL-", "project_learning": "LEARN-"}
    if interview_type not in prefixes:
        _project_fail("invalid_project_evidence", "interview_type")
    if not str(event.get("sessionId", "")).startswith(prefixes[interview_type]):
        _project_fail("invalid_project_evidence", "session_id_prefix")
    questions = event.get("questions")
    if not isinstance(questions, list) or not questions:
        _project_fail("invalid_project_evidence", "questions")
    project_ids: set[str] = set()
    question_ids: set[object] = set()
    attempt_ids: set[str] = set()
    project_questions = 0
    for question in questions:
        if not isinstance(question, dict):
            _project_fail("invalid_project_evidence", "question")
        if "projectEvidence" in question:
            validate_project_question(question)
            project_questions += 1
            project_ids.add(question["projectEvidence"]["project"]["projectId"])
            attempt_id = question["projectEvidence"]["attemptId"]
            if attempt_id in attempt_ids:
                _project_fail("attempt_identity_conflict", "duplicate_in_session")
            attempt_ids.add(attempt_id)
        question_id = question.get("questionId")
        if isinstance(question_id, str) and question_id.strip():
            if question_id in question_ids:
                _project_fail("invalid_project_evidence", "duplicate_question")
            question_ids.add(question_id)
        if _project_bytes(question) > MAX_PROJECT_QUESTION_BYTES:
            _project_fail("project_envelope_too_large", "question")
    if project_questions == 0:
        _project_fail("invalid_project_evidence", "no_project_question")
    if interview_type == "project_learning":
        if project_questions != len(questions):
            _project_fail("invalid_project_evidence", "learning_requires_evidence")
        if len(project_ids) != 1:
            _project_fail("invalid_project_evidence", "learning_single_project")
    if _project_bytes(event) > MAX_PROJECT_ENVELOPE_BYTES:
        _project_fail("project_envelope_too_large", "event")


def validate_project_review_event(event: object) -> None:
    """Review-level structural rules for project v1."""
    if event.get("projectContractVersion") != PROJECT_CONTRACT_VERSION:
        _project_fail("project_contract_version_unsupported", "version")
    interview_type = event.get("interviewType")
    prefixes = {"mock": "MOCK-", "real": "REAL-", "project_learning": "LEARN-"}
    if interview_type not in prefixes:
        _project_fail("invalid_project_evidence", "interview_type")
    if not str(event.get("sessionId", "")).startswith(prefixes[interview_type]):
        _project_fail("invalid_project_evidence", "session_id_prefix")
    if event.get("sourceType") != interview_type:
        _project_fail("review_source_mismatch", "source_type")
    if interview_type == "project_learning" and event.get("profileChanges"):
        _project_fail("invalid_project_evidence", "learning_profile_changes")
    seen_questions: set[object] = set()
    seen_attempts: set[str] = set()
    for item in event.get("questionReviews", []):
        question_id = item.get("questionId") if isinstance(item, dict) else None
        if question_id in seen_questions:
            _project_fail("assessment_question_mismatch", "duplicate_question")
        seen_questions.add(question_id)
        if not isinstance(item, dict) or "projectAssessment" not in item:
            continue
        _validate_assessment_shape(item["projectAssessment"])
        attempt_id = item["projectAssessment"]["attemptId"]
        if attempt_id in seen_attempts:
            _project_fail("assessment_question_mismatch", "duplicate_attempt")
        seen_attempts.add(attempt_id)
    if _project_bytes(event) > MAX_PROJECT_ENVELOPE_BYTES:
        _project_fail("project_envelope_too_large", "event")
