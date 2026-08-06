from __future__ import annotations

import unittest

from scripts.mock_handoff import HandoffValidationError, create_mock_session, seal_review_handoff


def _context(**overrides: object) -> dict[str, object]:
    context: dict[str, object] = {
        "candidate_id": "TEST-20260806-001",
        "display_name": "测试候选人",
        "confirmed_by_user": True,
        "confirmed_at": "2026-08-06T00:00:00+00:00",
        "active_resume_id": None,
        "selected_domain": None,
    }
    context.update(overrides)
    return context


class MockHandoffTests(unittest.TestCase):
    def test_unconfirmed_context_cannot_create_session(self) -> None:
        with self.assertRaises(HandoffValidationError):
            create_mock_session(_context(confirmed_by_user=False), [])

    def test_no_resume_or_profile_defaults_to_java_backend(self) -> None:
        session = create_mock_session(_context(), [])

        self.assertEqual(session["selected_domain"], "java_backend")
        self.assertEqual(session["state"], "review_pending")
        self.assertTrue(str(session["session_id"]).startswith("MOCK-"))

    def test_resume_claims_drive_topics_without_becoming_evidence(self) -> None:
        questions = [
            {"question_id": "Q001", "domain": "java_backend", "source_tags": ["resume"], "topic_tags": [topic], "resume_claim_ids": ["CLAIM-001"]}
            for topic in ("Redis", "Lua", "MySQL", "MQ")
        ]
        session = create_mock_session(_context(active_resume_id="RES-001"), questions)

        self.assertEqual(set(session["covered_topics"]), {"Redis", "Lua", "MySQL", "MQ"})
        self.assertNotIn("evidence_delta", session)

    def test_excessive_or_ambiguous_retest_is_rejected(self) -> None:
        questions = [
            {"question_id": f"Q00{i}", "domain": "java_backend", "source_tags": ["profile_weakness"], "topic_tags": ["ConcurrentHashMap"]}
            for i in range(1, 4)
        ] + [
            {"question_id": f"Q00{i}", "domain": "java_backend", "source_tags": ["domain_knowledge"], "topic_tags": ["JVM"]}
            for i in range(4, 6)
        ]
        with self.assertRaises(HandoffValidationError):
            create_mock_session(_context(), questions)
        with self.assertRaises(HandoffValidationError):
            create_mock_session(_context(detected_domains=["java_backend", "llm_engineering"]), [])

    def test_sealed_handoff_keeps_candidate_lock_and_transcript_checksum(self) -> None:
        session = create_mock_session(_context(), [])
        handoff = seal_review_handoff(_context(), session, "Q: Redis\nA: 不会")

        self.assertEqual(handoff["candidate_id"], "TEST-20260806-001")
        self.assertEqual(handoff["state"], "review_pending")
        self.assertEqual(len(handoff["transcript_sha256"]), 64)

