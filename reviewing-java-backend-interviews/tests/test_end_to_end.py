from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.storage_protocol import LocalTestStore


def _session(candidate_id: str, source_type: str, sequence: str) -> dict[str, object]:
    prefix = "MOCK" if source_type == "mock_interview" else "REAL"
    return {
        "schema_version": "1.0",
        "candidate_id": candidate_id,
        "session_id": f"{prefix}-20260806-{sequence}",
        "source_type": source_type,
        "evidence_type": "system_transcript",
        "evidence_confidence": 0.6,
        "questions": [],
        "state": "review_pending",
    }


def _review(candidate_id: str, session_id: str, source_type: str, review_version: int = 1) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "candidate_id": candidate_id,
        "session_id": session_id,
        "review_version": review_version,
        "source_type": source_type,
        "evidence_type": "system_transcript",
        "evidence_confidence": 0.6,
        "questions": [],
        "basic_info": {"candidate_id": candidate_id, "session_id": session_id, "interview_type": source_type},
        "profile_change_summary": ["W-001：待验证"],
    }


def _event(candidate_id: str, session_id: str) -> dict[str, object]:
    return {
        "schema_version": "1.0", "event_id": f"EVT-{session_id}", "candidate_id": candidate_id,
        "session_id": session_id, "review_version": 1, "expected_profile_version": 0,
        "domain": "java_backend", "technical_weaknesses": [{"weakness_id": "W-001", "topic": "ConcurrentHashMap", "outcome": "failed", "variant_id": "initial"}],
        "general_competencies": {"communication": {"outcome": "improving"}},
    }


class InterviewLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.store = LocalTestStore(Path(self.temporary_directory.name), candidates=[
            {"schema_version": "1.0", "candidate_id": "TEST-20260806-001", "display_name": "测试候选人", "distinguishing_note": "后端"},
        ])
        self.context = self.store.confirm_candidate("TEST-20260806-001", True)

    def test_mock_review_applies_profile_and_writes_downloadable_artifacts(self) -> None:
        session = _session("TEST-20260806-001", "mock_interview", "001")
        self.store.seal_session(self.context, session, "Q: ConcurrentHashMap\nA: 不会")

        result = self.store.process_review(self.context, session, _review(session["candidate_id"], session["session_id"], "mock_interview"), _event(session["candidate_id"], session["session_id"]), user_confirmed=None)

        self.assertEqual(result["state"], "applied")
        self.assertEqual(self.store.current_profile("TEST-20260806-001")["profile_version"], 1)
        session_root = Path(result["session_root"])
        self.assertTrue((session_root / "raw_transcript.md").exists())
        self.assertTrue((session_root / "review_v1.json").exists())
        self.assertTrue((session_root / "review_report_v1.docx").exists())

    def test_real_review_waits_for_confirmation_or_rejection(self) -> None:
        session = _session("TEST-20260806-001", "real_interview", "002")
        self.store.seal_session(self.context, session, "Q: 算法\nA: 不会")
        review = _review(session["candidate_id"], session["session_id"], "real_interview")
        event = _event(session["candidate_id"], session["session_id"])

        pending = self.store.process_review(self.context, session, review, event, user_confirmed=None)
        self.assertEqual(pending["state"], "pending")
        self.assertEqual(self.store.current_profile("TEST-20260806-001")["profile_version"], 0)
        rejected = self.store.process_review(self.context, session, review, event, user_confirmed=False)
        self.assertEqual(rejected["state"], "rejected")
        self.assertEqual(self.store.current_profile("TEST-20260806-001")["profile_version"], 0)
        event_state = (Path(rejected["session_root"]) / "profile_update_event_v1.json").read_text(encoding="utf-8")
        self.assertIn('"state": "rejected"', event_state)
        with self.assertRaisesRegex(ValueError, "rejected"):
            self.store.process_review(self.context, session, review, event, user_confirmed=True)

    def test_real_review_applies_once_after_explicit_confirmation(self) -> None:
        session = _session("TEST-20260806-001", "real_interview", "003")
        self.store.seal_session(self.context, session, "Q: JVM 内存模型\nA: 有待补充")
        review = _review(session["candidate_id"], session["session_id"], "real_interview")
        event = _event(session["candidate_id"], session["session_id"])

        self.assertEqual(
            self.store.process_review(self.context, session, review, event, user_confirmed=None)["state"],
            "pending",
        )
        confirmed = self.store.process_review(self.context, session, review, event, user_confirmed=True)
        retried = self.store.process_review(self.context, session, review, event, user_confirmed=True)

        self.assertEqual(confirmed["state"], "applied")
        self.assertEqual(retried["state"], "applied")
        self.assertEqual(self.store.current_profile("TEST-20260806-001")["profile_version"], 1)

    def test_review_versions_are_immutable_and_persisted_separately(self) -> None:
        session = _session("TEST-20260806-001", "mock_interview", "004")
        self.store.seal_session(self.context, session, "Q: Redis\nA: 需要复盘")
        review_v1 = _review(session["candidate_id"], session["session_id"], "mock_interview", 1)
        event_v1 = _event(session["candidate_id"], session["session_id"])
        self.store.process_review(self.context, session, review_v1, event_v1, user_confirmed=None)

        altered_v1 = {**review_v1, "profile_change_summary": ["不允许覆盖"]}
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.store.process_review(self.context, session, altered_v1, event_v1, user_confirmed=None)

        review_v2 = _review(session["candidate_id"], session["session_id"], "mock_interview", 2)
        event_v2 = {
            **event_v1,
            "event_id": "EVT-MOCK-20260806-004-V2",
            "review_version": 2,
            "expected_profile_version": 1,
        }
        result = self.store.process_review(self.context, session, review_v2, event_v2, user_confirmed=None)
        session_root = Path(result["session_root"])
        self.assertTrue((session_root / "review_v1.json").exists())
        self.assertTrue((session_root / "review_v2.json").exists())
        self.assertTrue((session_root / "profile_update_event_v2.json").exists())

    def test_malformed_or_mismatched_review_cannot_be_persisted(self) -> None:
        session = _session("TEST-20260806-001", "mock_interview", "005")
        self.store.seal_session(self.context, session, "Q: MySQL\nA: 未完成")
        event = _event(session["candidate_id"], session["session_id"])
        malformed = {
            "schema_version": "1.0",
            "candidate_id": session["candidate_id"],
            "session_id": session["session_id"],
            "review_version": 1,
            "source_type": "mock_interview",
            "evidence_type": "system_transcript",
            "evidence_confidence": 0.6,
        }
        with self.assertRaisesRegex(ValueError, "Review missing"):
            self.store.process_review(self.context, session, malformed, event, user_confirmed=None)

        mismatched = {**_review(session["candidate_id"], session["session_id"], "mock_interview"), "source_type": "real_interview"}
        with self.assertRaisesRegex(ValueError, "matching source"):
            self.store.process_review(self.context, session, mismatched, event, user_confirmed=None)

    def test_process_review_rejects_path_like_session_id_before_reading_session(self) -> None:
        session = _session("TEST-20260806-001", "real_interview", "006")
        self.store.seal_session(self.context, session, "Q: 事务\nA: 未完成")
        escaped_id = "REAL-20260806-006/../REAL-20260806-006"
        escaped_session = {**session, "session_id": escaped_id}
        escaped_review = _review("TEST-20260806-001", escaped_id, "real_interview")
        escaped_event = {
            **_event("TEST-20260806-001", escaped_id),
            "event_id": "EVT-MOCK-20260806-006-ESCAPE",
        }

        with self.assertRaisesRegex(ValueError, "session_id"):
            self.store.process_review(
                self.context,
                escaped_session,
                escaped_review,
                escaped_event,
                user_confirmed=None,
            )
