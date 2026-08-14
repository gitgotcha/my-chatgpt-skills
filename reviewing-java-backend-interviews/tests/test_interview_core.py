from __future__ import annotations

import unittest

from scripts.interview_core import (
    ArtifactValidationError,
    ProfileConflictError,
    ReviewValidationError,
    apply_review_event,
    create_review_event,
    plan_question_sources,
    rebuild_profile,
    resolve_domain,
    validate_artifact,
)


USER_ID = "11111111-1111-4111-8111-111111111111"
SESSION_EVENT_ID = "22222222-2222-4222-8222-222222222222"
REVIEW_EVENT_ID = "33333333-3333-4333-8333-333333333333"
SESSION_ID = "REAL-20260814T000000Z-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def _review_identity() -> dict[str, object]:
    return {"userId": USER_ID, "username": "测试用户", "verified": True}


def _review_session() -> dict[str, object]:
    return {
        "schemaVersion": "1.2",
        "eventId": SESSION_EVENT_ID,
        "eventType": "interview.session.completed",
        "userId": USER_ID,
        "username": "测试用户",
        "sessionId": SESSION_ID,
        "interviewType": "real",
        "domain": "java-backend",
        "questions": [{"questionId": "Q-001"}],
    }


class ReviewEventContractTests(unittest.TestCase):
    def test_review_event_contains_schema_required_identity_and_evidence_fields(self) -> None:
        event = create_review_event(
            _review_identity(),
            _review_session(),
            question_reviews=[{
                "questionId": "Q-001",
                "assessment": "回答不完整",
                "evidence": {"source": "answer"},
                "recommendations": ["补充并发控制"],
            }],
            profile_changes=[{
                "kind": "weakness",
                "outcome": "failed",
                "domain": "java-backend",
                "weaknessId": "W-001",
                "evidenceRefs": ["Q-001"],
            }],
            recommendations=["复测缓存一致性"],
            apply_profile_changes=False,
            review_version=1,
            event_id=REVIEW_EVENT_ID,
            completed_at="2026-08-14T01:00:00Z",
            evidence_type="user_recall",
            evidence_confidence="low",
        )
        self.assertEqual(event["interviewType"], "real")
        self.assertEqual(event["domain"], "java-backend")
        self.assertEqual(event["sourceType"], "real")
        self.assertEqual(event["evidenceType"], "user_recall")
        self.assertEqual(event["evidenceConfidence"], "low")
        self.assertEqual(event["questionReviews"][0]["questionId"], "Q-001")
        self.assertEqual(event["profileChanges"][0]["kind"], "weakness")
        self.assertFalse(event["applyProfileChanges"])

    def test_review_requires_structured_question_and_profile_change_fields(self) -> None:
        common = {
            "identity": _review_identity(),
            "session": _review_session(),
            "profile_changes": [],
            "recommendations": [],
            "apply_profile_changes": False,
            "review_version": 1,
            "event_id": REVIEW_EVENT_ID,
            "completed_at": "2026-08-14T01:00:00Z",
        }
        with self.assertRaisesRegex(ReviewValidationError, "assessment"):
            create_review_event(
                common["identity"], common["session"],
                question_reviews=[{"questionId": "Q-001", "evidence": {}, "recommendations": []}],
                **{key: value for key, value in common.items() if key not in {"identity", "session"}},
            )
        with self.assertRaisesRegex(ReviewValidationError, "profileChanges require kind"):
            create_review_event(
                common["identity"], common["session"], question_reviews=[],
                profile_changes=[{"outcome": "failed"}],
                **{key: value for key, value in common.items() if key not in {"identity", "session", "profile_changes"}},
            )

    def test_review_rejects_unknown_nested_fields_and_invalid_optional_types(self) -> None:
        common = {
            "identity": _review_identity(),
            "session": _review_session(),
            "profile_changes": [],
            "recommendations": [],
            "apply_profile_changes": False,
            "review_version": 1,
            "event_id": REVIEW_EVENT_ID,
            "completed_at": "2026-08-14T01:00:00Z",
        }
        with self.assertRaisesRegex(ReviewValidationError, "unsupported fields"):
            create_review_event(
                common["identity"], common["session"],
                question_reviews=[{
                    "questionId": "Q-001", "assessment": "ok", "evidence": {},
                    "recommendations": [], "description": "not in contract",
                }],
                **{key: value for key, value in common.items() if key not in {"identity", "session"}},
            )
        with self.assertRaisesRegex(ReviewValidationError, "field domain"):
            create_review_event(
                common["identity"], common["session"], question_reviews=[],
                profile_changes=[{"kind": "weakness", "outcome": "failed", "domain": 7}],
                **{key: value for key, value in common.items() if key not in {"identity", "session", "profile_changes"}},
            )
        with self.assertRaisesRegex(ReviewValidationError, "evidenceRefs"):
            create_review_event(
                common["identity"], common["session"], question_reviews=[],
                profile_changes=[{"kind": "weakness", "outcome": "failed", "evidenceRefs": ["Q-1", 3]}],
                **{key: value for key, value in common.items() if key not in {"identity", "session", "profile_changes"}},
            )

    def test_review_rejects_boolean_versions_and_naive_timestamps(self) -> None:
        args = {
            "identity": _review_identity(),
            "session": _review_session(),
            "question_reviews": [],
            "profile_changes": [],
            "recommendations": [],
            "apply_profile_changes": False,
            "event_id": REVIEW_EVENT_ID,
        }
        with self.assertRaisesRegex(ReviewValidationError, "reviewVersion"):
            create_review_event(**args, review_version=True, completed_at="2026-08-14T01:00:00Z")
        with self.assertRaisesRegex(ReviewValidationError, "timezone"):
            create_review_event(**args, review_version=1, completed_at="2026-08-14T01:00:00")


class ArtifactValidationTests(unittest.TestCase):
    def test_candidate_context_requires_explicit_confirmation(self) -> None:
        with self.assertRaises(ArtifactValidationError):
            validate_artifact({"candidate_id": "TEST-20260806-001"}, "ConfirmedCandidateContext")


def _profile() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "candidate_id": "TEST-20260806-001",
        "profile_version": 0,
        "head_event_id": None,
        "domain_profiles": {"java_backend": {"weaknesses": {}}},
        "general_competencies": {},
    }


def _event(
    event_id: str,
    session_id: str,
    expected_version: int,
    outcome: str,
    variant_id: str,
    *,
    domain: str = "llm_engineering",
    replaces_event_id: str | None = None,
) -> dict[str, object]:
    event = {
        "schema_version": "1.0",
        "event_id": event_id,
        "candidate_id": "TEST-20260806-001",
        "session_id": session_id,
        "review_version": 1,
        "expected_profile_version": expected_version,
        "domain": domain,
        "technical_weaknesses": [{
            "weakness_id": "W-001",
            "topic": "ConcurrentHashMap",
            "outcome": outcome,
            "variant_id": variant_id,
        }],
        "general_competencies": {"communication": {"outcome": "improving"}},
    }
    if replaces_event_id is not None:
        event["replaces_event_id"] = replaces_event_id
    return event


class DeterministicProfileTests(unittest.TestCase):
    def test_apply_event_is_idempotent_and_domain_isolated(self) -> None:
        event = _event("EVT-001", "MOCK-20260806-001", 0, "failed", "v1")

        first = apply_review_event(_profile(), event)
        second = apply_review_event(first, event)

        self.assertEqual(second, first)
        self.assertIn("llm_engineering", first["domain_profiles"])
        self.assertNotIn("W-001", first["domain_profiles"]["java_backend"]["weaknesses"])
        self.assertIn("communication", first["general_competencies"])

    def test_stale_event_raises_profile_conflict(self) -> None:
        with self.assertRaises(ProfileConflictError):
            apply_review_event(_profile(), _event("EVT-002", "MOCK-20260806-002", 9, "failed", "v1"))

    def test_rebuild_replaces_v1_and_replays_later_event(self) -> None:
        v1 = _event("EVT-V1", "MOCK-20260806-010", 0, "failed", "v1", domain="java_backend")
        replacement = _event(
            "EVT-V1-R2", "MOCK-20260806-010", 0, "failed", "v2",
            domain="java_backend", replaces_event_id="EVT-V1",
        )
        later = _event("EVT-V2", "MOCK-20260806-011", 1, "passed", "v3", domain="java_backend")

        rebuilt = rebuild_profile(
            _profile(), [v1, replacement, later],
            {"superseded_event_id": "EVT-V1"},
        )

        self.assertEqual(rebuilt["head_event_id"], "EVT-V2")
        weakness = rebuilt["domain_profiles"]["java_backend"]["weaknesses"]["W-001"]
        self.assertEqual(weakness["status"], "improving")
        self.assertEqual(weakness["evidence_session_ids"], ["MOCK-20260806-010", "MOCK-20260806-011"])

    def test_weakness_requires_two_distinct_passing_variants_before_closing(self) -> None:
        profile = _profile()
        events = [
            _event("EVT-101", "MOCK-20260806-101", 0, "failed", "initial", domain="java_backend"),
            _event("EVT-102", "MOCK-20260806-102", 1, "passed", "scenario-a", domain="java_backend"),
            _event("EVT-103", "MOCK-20260806-103", 2, "passed", "scenario-a", domain="java_backend"),
        ]
        for event in events:
            profile = apply_review_event(profile, event)
        weakness = profile["domain_profiles"]["java_backend"]["weaknesses"]["W-001"]
        self.assertEqual(weakness["status"], "improving")

        closed = apply_review_event(
            profile,
            _event("EVT-104", "MOCK-20260806-104", 3, "passed", "scenario-b", domain="java_backend"),
        )
        self.assertEqual(
            closed["domain_profiles"]["java_backend"]["weaknesses"]["W-001"]["status"],
            "closed",
        )

    def test_domain_resolution_and_question_plan_are_safe(self) -> None:
        self.assertEqual(resolve_domain("algorithms", ["llm_engineering"], ["java_backend"]), "algorithms")
        self.assertEqual(resolve_domain(None, ["llm_engineering", "java_backend"], []), None)
        self.assertEqual(resolve_domain(None, [], []), "java_backend")

        with_resume = plan_question_sources(True, 10)
        without_resume = plan_question_sources(False, 10)
        self.assertEqual(sum(with_resume.values()), 10)
        self.assertEqual(sum(without_resume.values()), 10)
        self.assertLessEqual(with_resume["profile_weakness"] / 10, 0.4)
        self.assertLessEqual(without_resume["profile_weakness"] / 10, 0.4)
