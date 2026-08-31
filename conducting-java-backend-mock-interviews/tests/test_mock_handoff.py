from __future__ import annotations

import ast
import json
from pathlib import Path
import tempfile
import unittest

from scripts.mock_handoff import (
    HandoffValidationError,
    create_mock_session_event,
    save_session_copy,
)


USER_ID = "11111111-1111-4111-8111-111111111111"
EVENT_ID = "22222222-2222-4222-8222-222222222222"
SESSION_ID = "MOCK-20260814T000000Z-33333333-3333-4333-8333-333333333333"


def _identity(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {"userId": USER_ID, "username": "乔炳源", "verified": True}
    value.update(overrides)
    return value


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
    def test_unverified_identity_cannot_create_session_event(self) -> None:
        with self.assertRaisesRegex(HandoffValidationError, "verified identity"):
            create_mock_session_event(
                _identity(verified=False),
                [],
                started_at="2026-08-14T00:00:00Z",
                completed_at="2026-08-14T00:30:00Z",
                event_id=EVENT_ID,
                session_id=SESSION_ID,
            )

    def test_event_is_schema_12_and_preserves_original_answers(self) -> None:
        question = _question(1)
        event = create_mock_session_event(
            _identity(),
            [question],
            started_at="2026-08-14T00:00:00Z",
            completed_at="2026-08-14T00:30:00Z",
            event_id=EVENT_ID,
            session_id=SESSION_ID,
        )
        self.assertEqual(event["schemaVersion"], "1.2")
        self.assertEqual(event["eventType"], "interview.session.completed")
        self.assertEqual(event["eventKey"], f"{USER_ID}:interview:session:{SESSION_ID}:v1")
        self.assertEqual(event["questions"][0]["originalAnswer"], question["originalAnswer"])
        self.assertEqual(event["questions"][0]["followUps"], question["followUps"])
        self.assertEqual(event["status"], "review_pending")

    def test_weakness_retests_cannot_exceed_forty_percent(self) -> None:
        questions = [
            _question(index, sourceTags=["profileWeakness"] if index <= 3 else ["domainKnowledge"])
            for index in range(1, 6)
        ]
        with self.assertRaisesRegex(HandoffValidationError, "40%"):
            create_mock_session_event(
                _identity(), questions,
                started_at="2026-08-14T00:00:00Z",
                completed_at="2026-08-14T00:30:00Z",
                event_id=EVENT_ID,
                session_id=SESSION_ID,
            )

    def test_completed_session_requires_immutable_source_evidence(self) -> None:
        question = _question(1)
        for field in ("originalQuestion", "originalAnswer", "followUps", "timeline"):
            incomplete = dict(question)
            incomplete.pop(field)
            with self.subTest(field=field), self.assertRaisesRegex(HandoffValidationError, "question missing"):
                create_mock_session_event(
                    _identity(), [incomplete],
                    started_at="2026-08-14T00:00:00Z",
                    completed_at="2026-08-14T00:30:00Z",
                    event_id=EVENT_ID,
                    session_id=SESSION_ID,
                )

    def test_session_id_rejects_path_separators(self) -> None:
        with self.assertRaisesRegex(HandoffValidationError, "sessionId"):
            create_mock_session_event(
                _identity(), [],
                started_at="2026-08-14T00:00:00Z",
                completed_at="2026-08-14T00:30:00Z",
                event_id=EVENT_ID,
                session_id="MOCK-../escape",
            )

    def test_session_copy_uses_required_local_path(self) -> None:
        event = create_mock_session_event(
            _identity(), [_question(1)],
            started_at="2026-08-14T00:00:00Z",
            completed_at="2026-08-14T00:30:00Z",
            event_id=EVENT_ID,
            session_id=SESSION_ID,
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory)
            path = save_session_copy(event, output_root, "ok", {"fileId": "drive-1"})
            self.assertEqual(
                path,
                output_root / "interview" / USER_ID / f"interview-{SESSION_ID}-session.json",
            )
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["persistenceStatus"], "ok")
            self.assertEqual(saved["driveReceipt"], {"fileId": "drive-1"})
            self.assertEqual(saved["eventKey"], event["eventKey"])

    def test_cloud_failure_still_writes_pending_local_copy(self) -> None:
        event = create_mock_session_event(
            _identity(), [],
            started_at="2026-08-14T00:00:00Z",
            completed_at="2026-08-14T00:30:00Z",
            event_id=EVENT_ID,
            session_id=SESSION_ID,
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = save_session_copy(event, temporary_directory, "cloud_persistence_pending")
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["persistenceStatus"], "cloud_persistence_pending")
            self.assertNotIn("driveReceipt", saved)

    def test_session_event_never_embeds_local_output_paths(self) -> None:
        event = create_mock_session_event(
            _identity(), [_question(1)],
            started_at="2026-08-14T00:00:00Z",
            completed_at="2026-08-14T00:30:00Z",
            event_id=EVENT_ID,
            session_id=SESSION_ID,
        )
        # The submitted event must stay free of local copy bookkeeping.
        for forbidden in ("persistenceStatus", "driveReceipt"):
            self.assertNotIn(forbidden, event)
        serialized = json.dumps(event, ensure_ascii=False)
        for forbidden in ("outputs/", "output_root", "interview-", ".json"):
            self.assertNotIn(forbidden, serialized)

    def test_local_copy_stays_inside_the_provided_output_root(self) -> None:
        event = create_mock_session_event(
            _identity(), [_question(1)],
            started_at="2026-08-14T00:00:00Z",
            completed_at="2026-08-14T00:30:00Z",
            event_id=EVENT_ID,
            session_id=SESSION_ID,
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory)
            path = save_session_copy(event, output_root, "ok")
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
