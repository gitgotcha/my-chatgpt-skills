from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.interview_core import (
    ReviewValidationError,
    create_review_event,
    plan_question_sources,
    resolve_domain,
    save_review_json,
)


USER_ID = "11111111-1111-4111-8111-111111111111"
SESSION_EVENT_ID = "22222222-2222-4222-8222-222222222222"
REVIEW_EVENT_ID = "33333333-3333-4333-8333-333333333333"
SESSION_ID = "REAL-20260814T000000Z-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

INTERVIEW_CORE_SOURCE = Path(__file__).resolve().parent.parent / "scripts" / "interview_core.py"

# Assembled instead of written literally so this guard does not reintroduce the
# retired candidate-profile keys into the repository storage scan.
LEGACY_SOURCE_MARKERS = (
    "candidate" + "_id",
    "current" + "_profile",
    "profile" + "_version",
    "Candidate" + "Index",
)


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


def _review_event() -> dict[str, object]:
    return create_review_event(
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
    )


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
        self.assertEqual(event["schemaVersion"], "1.2")
        self.assertEqual(event["eventType"], "interview.review.completed")
        self.assertEqual(event["userId"], USER_ID)
        self.assertEqual(event["username"], "测试用户")
        self.assertEqual(event["sessionId"], SESSION_ID)
        self.assertEqual(event["reviewVersion"], 1)
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
        with self.assertRaisesRegex(ReviewValidationError, "timezone"):
            create_review_event(**args, review_version=1, completed_at="2026-08-14 01:00:00+00:00")


class LocalReportCopyTests(unittest.TestCase):
    def test_save_review_json_writes_below_the_user_id_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = save_review_json(_review_event(), Path(temporary_directory), "ok")
            self.assertEqual(
                path,
                Path(temporary_directory) / "interview" / USER_ID / f"interview-{SESSION_ID}-report.json",
            )
            self.assertTrue(path.exists())

    def test_saved_copy_records_persistence_status_and_receipt(self) -> None:
        import json

        receipt = {"fileId": "drive-file-1"}
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = save_review_json(_review_event(), Path(temporary_directory), "profile_cache_pending", receipt)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["persistenceStatus"], "profile_cache_pending")
            self.assertEqual(payload["driveReceipt"], receipt)
            self.assertEqual(payload["userId"], USER_ID)
            self.assertEqual(payload["sessionId"], SESSION_ID)
            self.assertEqual(payload["reviewVersion"], 1)

    def test_save_review_json_rejects_non_schema_12_input(self) -> None:
        event = _review_event()
        event["schemaVersion"] = "1.0"
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(ReviewValidationError, "schemaVersion 1.2"):
                save_review_json(event, Path(temporary_directory), "ok")

    def test_save_review_json_rejects_unsafe_session_id_and_unknown_status(self) -> None:
        event = _review_event()
        event["sessionId"] = "MOCK/../escape"
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(ReviewValidationError, "safe sessionId"):
                save_review_json(event, Path(temporary_directory), "ok")
            with self.assertRaisesRegex(ReviewValidationError, "unsupported persistenceStatus"):
                save_review_json(_review_event(), Path(temporary_directory), "saved")


class DomainAndSourcePlanningTests(unittest.TestCase):
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


class LegacyCandidateModelRemovalTests(unittest.TestCase):
    """The Worker profile-model.js is the only active profile reducer."""

    def test_candidate_profile_reducer_is_not_exposed(self) -> None:
        import scripts.interview_core as interview_core

        for name in (
            "validate_artifact",
            "apply_review_event",
            "rebuild_profile",
            "ArtifactValidationError",
            "CandidateLockError",
            "ProfileConflictError",
        ):
            self.assertFalse(hasattr(interview_core, name), f"{name} must not be part of the active contract")

    def test_module_source_has_no_legacy_candidate_contract(self) -> None:
        source = INTERVIEW_CORE_SOURCE.read_text(encoding="utf-8")
        for forbidden in LEGACY_SOURCE_MARKERS:
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
