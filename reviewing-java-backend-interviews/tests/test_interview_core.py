from __future__ import annotations

import unittest

from scripts.interview_core import (
    ArtifactValidationError,
    ProfileConflictError,
    apply_review_event,
    plan_question_sources,
    rebuild_profile,
    resolve_domain,
    validate_artifact,
)


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
