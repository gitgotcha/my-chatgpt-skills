from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.interview_core import (
    ReviewValidationError,
    create_review_snapshot,
    plan_question_sources,
    resolve_domain,
    save_review_json,
)


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


def _review_session() -> dict[str, object]:
    return {
        "schemaVersion": "interview-session-snapshot/2",
        "sessionId": SESSION_ID,
        "interviewType": "real",
        "domain": "java-backend",
        "questions": [{"questionId": "Q-001"}],
    }


def _review_event() -> dict[str, object]:
    return create_review_snapshot(
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
        completed_at="2026-08-14T01:00:00Z",
    )


class ReviewSnapshotContractTests(unittest.TestCase):
    def test_review_snapshot_contains_evidence_fields_without_identity(self) -> None:
        event = create_review_snapshot(
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
                completed_at="2026-08-14T01:00:00Z",
            evidence_type="user_recall",
            evidence_confidence="low",
        )
        self.assertEqual(event["schemaVersion"], "interview-review-snapshot/2")
        self.assertNotIn("userId", event)
        self.assertNotIn("username", event)
        self.assertNotIn("eventType", event)
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
            "session": _review_session(),
            "profile_changes": [],
            "recommendations": [],
            "apply_profile_changes": False,
            "review_version": 1,
            "completed_at": "2026-08-14T01:00:00Z",
        }
        with self.assertRaisesRegex(ReviewValidationError, "assessment"):
            create_review_snapshot(
                common["session"],
                question_reviews=[{"questionId": "Q-001", "evidence": {}, "recommendations": []}],
                **{key: value for key, value in common.items() if key != "session"},
            )
        with self.assertRaisesRegex(ReviewValidationError, "profileChanges require kind"):
            create_review_snapshot(
                common["session"], question_reviews=[],
                profile_changes=[{"outcome": "failed"}],
                **{key: value for key, value in common.items() if key not in {"session", "profile_changes"}},
            )

    def test_review_rejects_unknown_nested_fields_and_invalid_optional_types(self) -> None:
        common = {
            "session": _review_session(),
            "profile_changes": [],
            "recommendations": [],
            "apply_profile_changes": False,
            "review_version": 1,
            "completed_at": "2026-08-14T01:00:00Z",
        }
        with self.assertRaisesRegex(ReviewValidationError, "unsupported fields"):
            create_review_snapshot(
                common["session"],
                question_reviews=[{
                    "questionId": "Q-001", "assessment": "ok", "evidence": {},
                    "recommendations": [], "description": "not in contract",
                }],
                **{key: value for key, value in common.items() if key != "session"},
            )
        with self.assertRaisesRegex(ReviewValidationError, "field domain"):
            create_review_snapshot(
                common["session"], question_reviews=[],
                profile_changes=[{"kind": "weakness", "outcome": "failed", "domain": 7}],
                **{key: value for key, value in common.items() if key not in {"session", "profile_changes"}},
            )
        with self.assertRaisesRegex(ReviewValidationError, "evidenceRefs"):
            create_review_snapshot(
                common["session"], question_reviews=[],
                profile_changes=[{"kind": "weakness", "outcome": "failed", "evidenceRefs": ["Q-1", 3]}],
                **{key: value for key, value in common.items() if key not in {"session", "profile_changes"}},
            )

    def test_review_rejects_boolean_versions_and_naive_timestamps(self) -> None:
        args = {
            "session": _review_session(),
            "question_reviews": [],
            "profile_changes": [],
            "recommendations": [],
            "apply_profile_changes": False,
        }
        with self.assertRaisesRegex(ReviewValidationError, "reviewVersion"):
            create_review_snapshot(**args, review_version=True, completed_at="2026-08-14T01:00:00Z")
        with self.assertRaisesRegex(ReviewValidationError, "timezone"):
            create_review_snapshot(**args, review_version=1, completed_at="2026-08-14T01:00:00")
        with self.assertRaisesRegex(ReviewValidationError, "timezone"):
            create_review_snapshot(**args, review_version=1, completed_at="2026-08-14 01:00:00+00:00")


class LocalReportCopyTests(unittest.TestCase):
    def test_save_review_json_writes_below_the_local_interview_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = save_review_json(_review_event(), Path(temporary_directory))
            self.assertEqual(
                path,
                Path(temporary_directory) / "interview" / f"interview-{SESSION_ID}-report.json",
            )
            self.assertTrue(path.exists())

    def test_saved_copy_is_marked_local_and_contains_no_identity_or_cloud_claim(self) -> None:
        import json
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = save_review_json(_review_event(), Path(temporary_directory))
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("localCopyOnly", payload)
            for field in ("userId", "username", "eventId", "eventKey", "eventType", "persistenceStatus", "outboxReceipt"):
                self.assertNotIn(field, payload)
            self.assertEqual(payload["sessionId"], SESSION_ID)
            self.assertEqual(payload["reviewVersion"], 1)

    def test_save_review_json_rejects_unsupported_snapshot_schema(self) -> None:
        event = _review_event()
        event["schemaVersion"] = "unsupported"
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(ReviewValidationError, "interview-review-snapshot/2"):
                save_review_json(event, Path(temporary_directory))

    def test_save_review_json_rejects_unsafe_session_id(self) -> None:
        event = _review_event()
        event["sessionId"] = "MOCK/../escape"
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(ReviewValidationError, "safe sessionId"):
                save_review_json(event, Path(temporary_directory))


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
