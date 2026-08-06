from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.interview_core import CandidateLockError, ProfileConflictError
from scripts.storage_protocol import LocalTestStore


def _event() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "event_id": "EVT-STORE-001",
        "candidate_id": "TEST-A",
        "session_id": "MOCK-20260806-001",
        "review_version": 1,
        "expected_profile_version": 0,
        "domain": "java_backend",
        "technical_weaknesses": [],
        "general_competencies": {},
    }


def _session(candidate_id: str, session_id: str) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "candidate_id": candidate_id,
        "session_id": session_id,
        "source_type": "mock_interview",
        "evidence_type": "system_transcript",
        "evidence_confidence": 0.6,
        "questions": [],
        "state": "review_pending",
    }


class LocalTestStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.store = LocalTestStore(
            Path(self.temporary_directory.name),
            candidates=[
                {"schema_version": "1.0", "candidate_id": "TEST-A", "display_name": "王同学", "distinguishing_note": "后端"},
                {"schema_version": "1.0", "candidate_id": "TEST-B", "display_name": "王同学", "distinguishing_note": "算法"},
            ],
        )

    def test_unconfirmed_or_wrong_candidate_cannot_write_session(self) -> None:
        session = _session("TEST-A", "MOCK-20260806-001")
        with self.assertRaises(CandidateLockError):
            self.store.seal_session({"candidate_id": "TEST-A"}, session, "Q/A")

        context = self.store.confirm_candidate("TEST-A", True)
        with self.assertRaises(CandidateLockError):
            self.store.seal_session(context, _session("TEST-B", "MOCK-20260806-001"), "Q/A")

    def test_profile_conflict_keeps_current_profile_unchanged(self) -> None:
        context = self.store.confirm_candidate("TEST-A", True)
        before = self.store.current_profile("TEST-A")

        with self.assertRaises(ProfileConflictError):
            self.store.commit_profile_event(context, _event(), expected_version=9)

        self.assertEqual(self.store.current_profile("TEST-A"), before)

    def test_retrying_same_event_after_profile_switch_is_idempotent(self) -> None:
        context = self.store.confirm_candidate("TEST-A", True)
        first = self.store.commit_profile_event(context, _event(), expected_version=0)
        second = self.store.commit_profile_event(context, _event(), expected_version=0)

        self.assertEqual(first, second)
        self.assertEqual(second["profile_version"], 1)

    def test_session_failure_preserves_raw_transcript_for_recovery(self) -> None:
        context = self.store.confirm_candidate("TEST-A", True)
        session = _session("TEST-A", "MOCK-20260806-099")
        self.store.set_failpoint("after_session")

        with self.assertRaisesRegex(RuntimeError, "after_session"):
            self.store.seal_session(context, session, "Q: test\nA: test")

        session_root = Path(self.temporary_directory.name) / "candidates" / "TEST-A" / "sessions" / "MOCK-20260806-099"
        self.assertEqual((session_root / "raw_transcript.md").read_text(encoding="utf-8"), "Q: test\nA: test")

    def test_path_like_session_and_event_ids_are_rejected_before_writes(self) -> None:
        context = self.store.confirm_candidate("TEST-A", True)
        with self.assertRaises(CandidateLockError):
            self.store.seal_session(
                context,
                _session("TEST-A", "MOCK-20260806-001/../../escape"),
                "Q/A",
            )

        unsafe_event = {**_event(), "event_id": "EVT-STORE-001/../../escape"}
        with self.assertRaises(CandidateLockError):
            self.store.commit_profile_event(context, unsafe_event, expected_version=0)
