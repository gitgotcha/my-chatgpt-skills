"""Deterministic validation and profile operations for interview artifacts."""

from __future__ import annotations

from copy import deepcopy
from math import floor

SCHEMA_VERSION = "1.0"


class ArtifactValidationError(ValueError):
    """Raised when an artifact violates the project-owned schema contract."""


class CandidateLockError(ValueError):
    """Raised when a candidate context is absent or does not match an artifact."""


class ProfileConflictError(ValueError):
    """Raised when optimistic profile-version validation fails."""


_REQUIRED: dict[str, tuple[str, ...]] = {
    "ConfirmedCandidateContext": (
        "candidate_id", "display_name", "confirmed_by_user", "confirmed_at",
        "active_resume_id", "selected_domain",
    ),
    "InterviewSession": (
        "schema_version", "session_id", "candidate_id", "source_type", "evidence_type",
        "evidence_confidence", "questions", "state",
    ),
    "Review": (
        "schema_version", "candidate_id", "session_id", "review_version", "source_type",
        "evidence_type", "evidence_confidence", "questions",
    ),
    "ProfileUpdateEvent": (
        "schema_version", "event_id", "candidate_id", "session_id", "review_version",
        "expected_profile_version", "domain", "technical_weaknesses", "general_competencies",
    ),
}


def validate_artifact(data: dict[str, object], schema_name: str) -> dict[str, object]:
    """Validate the stable fields required by the named shared artifact."""
    if not isinstance(data, dict):
        raise ArtifactValidationError(f"{schema_name} must be an object")
    required = _REQUIRED.get(schema_name)
    if required is None:
        raise ArtifactValidationError(f"unsupported schema: {schema_name}")
    missing = [key for key in required if key not in data]
    if missing:
        raise ArtifactValidationError(f"{schema_name} missing: {', '.join(missing)}")
    if schema_name == "ConfirmedCandidateContext":
        if data["confirmed_by_user"] is not True:
            raise ArtifactValidationError("candidate must be explicitly confirmed")
        if not isinstance(data["candidate_id"], str) or not data["candidate_id"].startswith(("CAND-", "TEST-")):
            raise ArtifactValidationError("candidate_id must be a stable candidate ID")
    elif schema_name in {"InterviewSession", "Review", "ProfileUpdateEvent"}:
        if data["schema_version"] != SCHEMA_VERSION:
            raise ArtifactValidationError(f"{schema_name} has unsupported schema_version")
        if not isinstance(data["candidate_id"], str) or not data["candidate_id"].startswith(("CAND-", "TEST-")):
            raise ArtifactValidationError(f"{schema_name} requires a stable candidate_id")
        if not isinstance(data["session_id"], str) or not data["session_id"].startswith(("MOCK-", "REAL-")):
            raise ArtifactValidationError(f"{schema_name} requires a stable session_id")
        if schema_name in {"InterviewSession", "Review"}:
            if data.get("source_type") not in {"mock_interview", "real_interview"}:
                raise ArtifactValidationError(f"{schema_name} has invalid source_type")
            if not isinstance(data.get("evidence_confidence"), (int, float)) or not 0 <= data["evidence_confidence"] <= 1:
                raise ArtifactValidationError(f"{schema_name} has invalid evidence_confidence")
            if not isinstance(data.get("questions"), list):
                raise ArtifactValidationError(f"{schema_name} missing valid questions")
        if schema_name == "InterviewSession":
            if data.get("state") not in {"review_pending", "reviewed", "cloud_persistence_pending"}:
                raise ArtifactValidationError("InterviewSession has invalid state")
        elif schema_name == "Review":
            if not isinstance(data.get("review_version"), int) or data["review_version"] < 1:
                raise ArtifactValidationError("Review has invalid review_version")
        else:
            if not isinstance(data.get("event_id"), str) or not data["event_id"].startswith("EVT-"):
                raise ArtifactValidationError("ProfileUpdateEvent requires a stable event_id")
            if not isinstance(data.get("review_version"), int) or data["review_version"] < 1:
                raise ArtifactValidationError("ProfileUpdateEvent has invalid review_version")
            if not isinstance(data.get("expected_profile_version"), int) or data["expected_profile_version"] < 0:
                raise ArtifactValidationError("ProfileUpdateEvent has invalid expected_profile_version")
            if not isinstance(data.get("domain"), str) or not data["domain"]:
                raise ArtifactValidationError("ProfileUpdateEvent requires a domain")
            if not isinstance(data.get("technical_weaknesses"), list) or not isinstance(data.get("general_competencies"), dict):
                raise ArtifactValidationError("ProfileUpdateEvent has invalid deltas")
    return deepcopy(data)


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


def _application_key(event: dict[str, object]) -> str:
    return "|".join(str(event[key]) for key in ("candidate_id", "session_id", "review_version"))


def apply_review_event(profile: dict[str, object], event: dict[str, object]) -> dict[str, object]:
    """Return a new profile after one validated, idempotent event application."""
    candidate_id = event.get("candidate_id")
    if candidate_id != profile.get("candidate_id"):
        raise CandidateLockError("event candidate_id does not match profile lock")
    key = _application_key(event)
    applied_keys = list(profile.get("applied_event_keys", []))
    if key in applied_keys:
        return deepcopy(profile)
    expected = event.get("expected_profile_version")
    if expected != profile.get("profile_version"):
        raise ProfileConflictError("expected_profile_version does not match current profile")

    updated = deepcopy(profile)
    domain = event.get("domain")
    if not isinstance(domain, str) or not domain:
        raise ArtifactValidationError("profile event requires a domain")
    domain_profiles = updated.setdefault("domain_profiles", {})
    domain_profile = domain_profiles.setdefault(domain, {"weaknesses": {}, "next_interview_guidance": []})
    weaknesses = domain_profile.setdefault("weaknesses", {})
    session_id = str(event.get("session_id"))

    for delta in event.get("technical_weaknesses", []):
        if not isinstance(delta, dict):
            raise ArtifactValidationError("technical_weaknesses entries must be objects")
        weakness_id = delta.get("weakness_id")
        outcome = delta.get("outcome")
        variant_id = delta.get("variant_id")
        if not isinstance(weakness_id, str) or outcome not in {"failed", "passed"} or not isinstance(variant_id, str):
            raise ArtifactValidationError("invalid technical weakness delta")
        weakness = weaknesses.setdefault(weakness_id, {
            "topic": delta.get("topic", weakness_id),
            "status": "open",
            "evidence_session_ids": [],
            "passing_session_ids": [],
            "variant_ids": [],
            "passing_variant_ids": [],
        })
        if session_id not in weakness["evidence_session_ids"]:
            weakness["evidence_session_ids"].append(session_id)
        if variant_id not in weakness["variant_ids"]:
            weakness["variant_ids"].append(variant_id)
        if outcome == "failed":
            weakness["status"] = "open"
        else:
            if session_id not in weakness["passing_session_ids"]:
                weakness["passing_session_ids"].append(session_id)
            passing_variants = weakness.setdefault("passing_variant_ids", [])
            if variant_id not in passing_variants:
                passing_variants.append(variant_id)
            if len(weakness["passing_session_ids"]) >= 2 and len(passing_variants) >= 2:
                weakness["status"] = "closed"
            else:
                weakness["status"] = "improving"

    general = updated.setdefault("general_competencies", {})
    for competency, delta in event.get("general_competencies", {}).items():
        if not isinstance(delta, dict):
            raise ArtifactValidationError("general competency delta must be an object")
        record = general.setdefault(competency, {"evidence_session_ids": [], "outcomes": []})
        if session_id not in record["evidence_session_ids"]:
            record["evidence_session_ids"].append(session_id)
        outcome = delta.get("outcome")
        if outcome and outcome not in record["outcomes"]:
            record["outcomes"].append(outcome)

    updated["profile_version"] = int(updated["profile_version"]) + 1
    updated["head_event_id"] = event.get("event_id")
    updated["applied_event_keys"] = applied_keys + [key]
    return updated


def rebuild_profile(
    snapshot: dict[str, object], active_events: list[dict[str, object]], correction: dict[str, object] | None
) -> dict[str, object]:
    """Rebuild from a snapshot, omitting one superseded event and replaying the rest."""
    superseded = correction.get("superseded_event_id") if correction else None
    rebuilt = deepcopy(snapshot)
    for event in active_events:
        if event.get("event_id") == superseded:
            continue
        rebuilt = apply_review_event(rebuilt, event)
    return rebuilt
