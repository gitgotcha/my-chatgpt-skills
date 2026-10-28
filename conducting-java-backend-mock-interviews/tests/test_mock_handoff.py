from __future__ import annotations

import ast
import json
from pathlib import Path
import tempfile
import unittest

from scripts.mock_handoff import (
    HandoffValidationError,
    create_mock_session_snapshot,
    save_session_copy,
)


SESSION_ID = "MOCK-20260814T000000Z-33333333-3333-4333-8333-333333333333"


def _question(number: int, **overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "questionId": f"Q-{number:03d}",
        "domain": "java-backend",
        "sourceTags": ["domainKnowledge"],
        "topicTags": ["cache"],
        "originalQuestion": "如何保证缓存一致性？",
        "originalAnswer": "先说明失效策略，再说明并发控制。",
        "followUps": [{"question": "如何处理并发回源？", "answer": "使用单飞。"}],
        "timeline": [{"at": "2026-08-14T00:01:00Z", "kind": "answer"}],
    }
    value.update(overrides)
    return value


class MockHandoffTests(unittest.TestCase):
    def test_session_snapshot_does_not_need_identity(self) -> None:
        snapshot = create_mock_session_snapshot(
            [], started_at="2026-08-14T00:00:00Z",
            completed_at="2026-08-14T00:30:00Z", session_id=SESSION_ID,
        )
        self.assertNotIn("userId", snapshot)
        self.assertNotIn("username", snapshot)

    def test_snapshot_preserves_original_answers(self) -> None:
        question = _question(1)
        event = create_mock_session_snapshot(
            [question],
            started_at="2026-08-14T00:00:00Z",
            completed_at="2026-08-14T00:30:00Z",
            session_id=SESSION_ID,
        )
        self.assertEqual(event["schemaVersion"], "interview-session-snapshot/2")
        self.assertEqual(event["questions"][0]["originalAnswer"], question["originalAnswer"])
        self.assertEqual(event["questions"][0]["followUps"], question["followUps"])
        self.assertEqual(event["status"], "review_pending")

    def test_weakness_retests_cannot_exceed_forty_percent(self) -> None:
        questions = [
            _question(index, sourceTags=["profileWeakness"] if index <= 3 else ["domainKnowledge"])
            for index in range(1, 6)
        ]
        with self.assertRaisesRegex(HandoffValidationError, "40%"):
            create_mock_session_snapshot(
                questions,
                started_at="2026-08-14T00:00:00Z",
                completed_at="2026-08-14T00:30:00Z",
                session_id=SESSION_ID,
            )

    def test_completed_session_requires_immutable_source_evidence(self) -> None:
        question = _question(1)
        for field in ("originalQuestion", "originalAnswer", "followUps", "timeline"):
            incomplete = dict(question)
            incomplete.pop(field)
            with self.subTest(field=field), self.assertRaisesRegex(HandoffValidationError, "question missing"):
                create_mock_session_snapshot(
                    [incomplete],
                    started_at="2026-08-14T00:00:00Z",
                    completed_at="2026-08-14T00:30:00Z",
                    session_id=SESSION_ID,
                )

    def test_session_id_rejects_path_separators(self) -> None:
        with self.assertRaisesRegex(HandoffValidationError, "sessionId"):
            create_mock_session_snapshot(
                [],
                started_at="2026-08-14T00:00:00Z",
                completed_at="2026-08-14T00:30:00Z",
                session_id="MOCK-../escape",
            )

    def test_session_copy_uses_required_local_path(self) -> None:
        event = create_mock_session_snapshot(
            [_question(1)],
            started_at="2026-08-14T00:00:00Z",
            completed_at="2026-08-14T00:30:00Z",
            session_id=SESSION_ID,
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory)
            path = save_session_copy(event, output_root)
            self.assertEqual(
                path,
                output_root / "interview" / f"interview-{SESSION_ID}-session.json",
            )
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("localCopyOnly", saved)
            self.assertNotIn("userId", saved)

    def test_cloud_failure_still_writes_pending_local_copy(self) -> None:
        event = create_mock_session_snapshot(
            [],
            started_at="2026-08-14T00:00:00Z",
            completed_at="2026-08-14T00:30:00Z",
            session_id=SESSION_ID,
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = save_session_copy(event, temporary_directory)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("localCopyOnly", saved)

    def test_session_snapshot_has_no_local_output_paths(self) -> None:
        event = create_mock_session_snapshot(
            [_question(1)],
            started_at="2026-08-14T00:00:00Z",
            completed_at="2026-08-14T00:30:00Z",
            session_id=SESSION_ID,
        )
        for forbidden in ("persistenceStatus", "outboxReceipt", "driveReceipt", "userId", "username", "eventType", "eventKey", "eventId"):
            self.assertNotIn(forbidden, event)
        serialized = json.dumps(event, ensure_ascii=False)
        for forbidden in ("outputs/", "output_root", "outputs/interview/", ".json"):
            self.assertNotIn(forbidden, serialized)

    def test_local_copy_stays_inside_the_provided_output_root(self) -> None:
        event = create_mock_session_snapshot(
            [_question(1)],
            started_at="2026-08-14T00:00:00Z",
            completed_at="2026-08-14T00:30:00Z",
            session_id=SESSION_ID,
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory)
            path = save_session_copy(event, output_root)
            self.assertTrue(path.is_relative_to(output_root))

    def test_handoff_module_imports_only_safe_stdlib(self) -> None:
        source = (
            Path(__file__).resolve().parents[1] / "scripts" / "mock_handoff.py"
        ).read_text(encoding="utf-8")
        allowed_roots = {"__future__", "copy", "datetime", "json", "pathlib", "re", "typing"}
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(alias.name.split(".")[0], allowed_roots, alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    self.assertIn(node.module.split(".")[0], allowed_roots, node.module)


# ---------------------------------------------------------------------------
# Project contract v1 (design 2026-10-24, §5): additive constructor support.
# The legacy assertions above keep their original meaning; these cases only
# cover the new opt-in path.
# ---------------------------------------------------------------------------
PROJECT_ID = "44444444-4444-4444-8444-444444444444"
OTHER_PROJECT_ID = "55555555-5555-4555-8555-555555555555"
LEARN_SESSION_ID = "LEARN-20260814T000000Z-44444444-4444-4444-8444-444444444444"


def _project_evidence(
    number: int,
    *,
    project_id: str = PROJECT_ID,
    attempt_id: str | None = None,
) -> dict[str, object]:
    return {
        "project": {
            "projectId": project_id,
            "displayName": "12306",
            "basis": {
                "kind": "source_learning",
                "key": "source-learning:train-12306:local-verified",
            },
            "resumeVersion": None,
            "resumeClaimIds": [],
            "sourceRevision": "worktree:2026-10-23",
        },
        "attemptId": attempt_id or f"33333333-3333-4333-8333-{number:012d}",
        "questionKey": f"ticket.query.q{number}",
        "variantId": f"variant-{number}",
        "variantAxes": ["control_flow"],
        "purpose": "targeted_retest",
        "sourceSkill": "conducting-java-backend-mock-interviews",
        "provenance": {
            "answerOrigin": "actual_user",
            "assistance": "none",
            "exactAnswerSeenBefore": False,
            "exposureGroupId": f"exposure-{number}",
        },
        "sourceRefs": ["S-local:SeatMarginCacheLoader.java:61"],
    }


def _project_question(
    number: int,
    *,
    project_id: str = PROJECT_ID,
    attempt_id: str | None = None,
    evidence: dict[str, object] | None = None,
    **overrides: object,
) -> dict[str, object]:
    value = _question(number, **overrides)
    value["projectEvidence"] = (
        _project_evidence(number, project_id=project_id, attempt_id=attempt_id)
        if evidence is None
        else evidence
    )
    return value


class ProjectContractHandoffTests(unittest.TestCase):
    def _create(
        self,
        questions: list[dict[str, object]],
        *,
        mode: str = "project_targeted",
        project_contract_version: int | None = 1,
        session_id: str = SESSION_ID,
    ) -> dict[str, object]:
        return create_mock_session_snapshot(
            questions,
            started_at="2026-08-14T00:00:00Z",
            completed_at="2026-08-14T00:30:00Z",
            session_id=session_id,
            mode=mode,
            project_contract_version=project_contract_version,
        )

    def test_default_call_creates_a_full_mock_snapshot(self) -> None:
        event = create_mock_session_snapshot(
            [_question(1)],
            started_at="2026-08-14T00:00:00Z",
            completed_at="2026-08-14T00:30:00Z",
            session_id=SESSION_ID,
        )
        self.assertNotIn("projectContractVersion", event)
        self.assertEqual(event["interviewType"], "mock")

    def test_project_targeted_snapshot_records_contract_version_and_evidence(self) -> None:
        question = _project_question(1)
        event = self._create([question])

        self.assertEqual(event["projectContractVersion"], 1)
        self.assertEqual(event["interviewType"], "mock")
        self.assertEqual(
            event["questions"][0]["projectEvidence"],
            question["projectEvidence"],
        )
        self.assertIsNot(
            event["questions"][0]["projectEvidence"],
            question["projectEvidence"],
        )

    def test_learn_prefix_maps_to_project_learning(self) -> None:
        event = self._create(
            [_project_question(1)],
            mode="project_learning",
            session_id=LEARN_SESSION_ID,
        )

        self.assertEqual(event["interviewType"], "project_learning")
        self.assertEqual(event["projectContractVersion"], 1)
        self.assertTrue(event["sessionId"].startswith("LEARN-"))

    def test_learn_prefix_is_accepted_with_the_contract_in_default_mode(self) -> None:
        # The contract flag, not the mode label, is what allows `LEARN-`; the
        # result is unambiguously a project-learning session.
        event = self._create(
            [_project_question(1)],
            mode="full_mock",
            session_id=LEARN_SESSION_ID,
        )

        self.assertEqual(event["interviewType"], "project_learning")
        self.assertEqual(event["projectContractVersion"], 1)

    def test_learn_prefix_requires_a_project_contract(self) -> None:
        with self.assertRaisesRegex(HandoffValidationError, "LEARN-|projectContractVersion"):
            create_mock_session_snapshot(
                [_question(1)],
                started_at="2026-08-14T00:00:00Z",
                completed_at="2026-08-14T00:30:00Z",
                session_id=LEARN_SESSION_ID,
            )

    def test_unknown_project_contract_version_is_rejected(self) -> None:
        with self.assertRaisesRegex(HandoffValidationError, "projectContractVersion"):
            self._create([_project_question(1)], project_contract_version=2)

    def test_project_targeted_requires_the_contract_flag(self) -> None:
        with self.assertRaisesRegex(HandoffValidationError, "projectContractVersion"):
            self._create([_project_question(1)], project_contract_version=None)

    def test_full_mock_rejects_project_evidence_without_contract(self) -> None:
        with self.assertRaisesRegex(HandoffValidationError, "projectEvidence"):
            create_mock_session_snapshot(
                [_project_question(1)],
                started_at="2026-08-14T00:00:00Z",
                completed_at="2026-08-14T00:30:00Z",
                session_id=SESSION_ID,
            )

    def test_project_contract_requires_evidence_on_every_question(self) -> None:
        with self.assertRaisesRegex(HandoffValidationError, "projectEvidence"):
            self._create([_project_question(1), _question(2)])

    def test_project_targeted_rejects_mixed_project_ids(self) -> None:
        with self.assertRaisesRegex(HandoffValidationError, "one project"):
            self._create([
                _project_question(1, project_id=PROJECT_ID),
                _project_question(2, project_id=OTHER_PROJECT_ID),
            ])

    def test_project_contract_rejects_duplicate_attempt_ids(self) -> None:
        shared_attempt = "33333333-3333-4333-8333-000000000123"
        with self.assertRaisesRegex(HandoffValidationError, "attempt"):
            self._create([
                _project_question(1, attempt_id=shared_attempt),
                _project_question(2, attempt_id=shared_attempt),
            ])

    def test_project_contract_rejects_malformed_evidence(self) -> None:
        bad_purpose = _project_evidence(1)
        bad_purpose["purpose"] = "daily_recap"
        with self.assertRaisesRegex(HandoffValidationError, "purpose"):
            self._create([_project_question(1, evidence=bad_purpose)])

        missing_refs = _project_evidence(1)
        missing_refs.pop("sourceRefs")
        with self.assertRaisesRegex(HandoffValidationError, "projectEvidence"):
            self._create([_project_question(1, evidence=missing_refs)])

    def test_targeted_mode_skips_the_forty_percent_weakness_ceiling(self) -> None:
        questions = [
            _project_question(number, sourceTags=["profileWeakness"])
            for number in range(1, 6)
        ]
        event = self._create(questions)

        self.assertEqual(len(event["questions"]), 5)
        self.assertEqual(
            [item["projectEvidence"]["attemptId"] for item in event["questions"]],
            [f"33333333-3333-4333-8333-{number:012d}" for number in range(1, 6)],
        )

    def test_full_mock_project_contract_keeps_the_forty_percent_ceiling(self) -> None:
        questions = [
            _project_question(number, sourceTags=["profileWeakness"])
            for number in range(1, 6)
        ]
        with self.assertRaisesRegex(HandoffValidationError, "40%"):
            self._create(questions, mode="full_mock")
