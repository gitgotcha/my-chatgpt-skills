"""Filesystem-only storage double for deterministic local tests.

This module deliberately does not implement a Google Drive client. Runtime
workflows must use the available Drive connector; tests inject this local
adapter underneath a temporary directory.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from scripts.interview_core import (
    ArtifactValidationError,
    CandidateLockError,
    ProfileConflictError,
    apply_review_event,
    validate_artifact,
)
from scripts.create_review_report import create_review_report


def _json_write_atomic(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _json_read(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_write_immutable(path: Path, value: dict[str, object]) -> None:
    if path.exists():
        if _json_read(path) != value:
            raise ArtifactValidationError(f"immutable artifact conflict: {path.name}")
        return
    _json_write_atomic(path, value)


_ID_PATTERNS = {
    "candidate": re.compile(r"(?:CAND|TEST)-[A-Za-z0-9-]+\Z"),
    "session": re.compile(r"(?:MOCK|REAL)-[A-Za-z0-9-]+\Z"),
    "event": re.compile(r"EVT-[A-Za-z0-9-]+\Z"),
}


def _require_stable_id(value: object, kind: str) -> str:
    if not isinstance(value, str) or _ID_PATTERNS[kind].fullmatch(value) is None:
        raise CandidateLockError(f"{kind}_id must be a stable identifier")
    return value


class LocalTestStore:
    """A confined, temporary-root persistence double used only by tests."""

    def __init__(self, root: Path, *, candidates: list[dict[str, object]]) -> None:
        self.root = root
        self._failpoint: str | None = None
        self.root.mkdir(parents=True, exist_ok=True)
        _json_write_atomic(self.root / "system" / "candidate_index.json", {
            "schema_version": "1.0", "candidates": candidates,
        })

    def set_failpoint(self, name: str | None) -> None:
        if name not in {None, "after_session", "after_review", "after_report", "after_profile_switch"}:
            raise ValueError("unsupported failpoint")
        self._failpoint = name

    def _raise_at(self, name: str) -> None:
        if self._failpoint == name:
            raise RuntimeError(f"injected failure: {name}")

    def read_candidate_summary(self, query: str | None = None) -> list[dict[str, object]]:
        candidates = _json_read(self.root / "system" / "candidate_index.json")["candidates"]
        if query is None:
            return list(candidates)
        lowered = query.lower()
        return [candidate for candidate in candidates if lowered in str(candidate["candidate_id"]).lower()
                or lowered in str(candidate["display_name"]).lower()]

    def confirm_candidate(self, candidate_id: str, confirmed_by_user: bool) -> dict[str, object]:
        if confirmed_by_user is not True:
            raise CandidateLockError("candidate confirmation was not supplied")
        candidates = self.read_candidate_summary(candidate_id)
        selected = [candidate for candidate in candidates if candidate["candidate_id"] == candidate_id]
        if len(selected) != 1:
            raise CandidateLockError("candidate must be selected by stable candidate_id")
        candidate = selected[0]
        return {
            "candidate_id": candidate_id,
            "display_name": candidate["display_name"],
            "confirmed_by_user": True,
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
            "active_resume_id": None,
            "selected_domain": None,
        }

    def _assert_context(self, context: dict[str, object], candidate_id: str) -> None:
        try:
            validated = validate_artifact(context, "ConfirmedCandidateContext")
        except ArtifactValidationError as error:
            raise CandidateLockError(str(error)) from error
        if validated["candidate_id"] != candidate_id:
            raise CandidateLockError("candidate context does not match artifact")

    def _candidate_root(self, candidate_id: str) -> Path:
        _require_stable_id(candidate_id, "candidate")
        return self.root / "candidates" / candidate_id

    def _profile_path(self, candidate_id: str) -> Path:
        return self._candidate_root(candidate_id) / "profile" / "current_profile.json"

    def current_profile(self, candidate_id: str) -> dict[str, object]:
        path = self._profile_path(candidate_id)
        if not path.exists():
            _json_write_atomic(path, {
                "schema_version": "1.0", "candidate_id": candidate_id,
                "profile_version": 0, "head_event_id": None,
                "domain_profiles": {}, "general_competencies": {}, "applied_event_keys": [],
            })
        return _json_read(path)

    def seal_session(self, context: dict[str, object], session: dict[str, object], transcript: str) -> Path:
        validate_artifact(session, "InterviewSession")
        candidate_id = session.get("candidate_id")
        session_id = session.get("session_id")
        if not isinstance(candidate_id, str) or not isinstance(session_id, str):
            raise CandidateLockError("session requires candidate_id and session_id")
        _require_stable_id(candidate_id, "candidate")
        _require_stable_id(session_id, "session")
        self._assert_context(context, candidate_id)
        session_root = self._candidate_root(candidate_id) / "sessions" / session_id
        session_root.mkdir(parents=True, exist_ok=False)
        _json_write_atomic(session_root / "session.json", session)
        (session_root / "raw_transcript.md").write_text(transcript, encoding="utf-8")
        _json_write_atomic(session_root / "recovery_state.json", {
            "schema_version": "1.0", "candidate_id": candidate_id,
            "session_id": session_id, "state": "review_pending",
        })
        self._raise_at("after_session")
        return session_root

    def commit_profile_event(
        self, context: dict[str, object], event: dict[str, object], expected_version: int
    ) -> dict[str, object]:
        validate_artifact(event, "ProfileUpdateEvent")
        candidate_id = event.get("candidate_id")
        if not isinstance(candidate_id, str):
            raise CandidateLockError("event requires candidate_id")
        _require_stable_id(candidate_id, "candidate")
        _require_stable_id(event.get("session_id"), "session")
        _require_stable_id(event.get("event_id"), "event")
        self._assert_context(context, candidate_id)
        if event.get("expected_profile_version") != expected_version:
            raise ProfileConflictError("caller and event expected versions differ")
        current = self.current_profile(candidate_id)
        application_key = "|".join(
            str(event[key]) for key in ("candidate_id", "session_id", "review_version")
        )
        if application_key in current.get("applied_event_keys", []):
            return current
        if current["profile_version"] != expected_version:
            raise ProfileConflictError("current profile changed before commit")
        self._raise_at("after_review")
        updated = apply_review_event(current, event)
        self._raise_at("after_report")
        profile_root = self._candidate_root(candidate_id) / "profile"
        _json_write_immutable(profile_root / "history" / f"profile_v{current['profile_version']}.json", current)
        _json_write_immutable(self._candidate_root(candidate_id) / "events" / f"{event['event_id']}.json", event)
        _json_write_atomic(self._profile_path(candidate_id), updated)
        self._raise_at("after_profile_switch")
        return updated

    def process_review(
        self,
        context: dict[str, object],
        session: dict[str, object],
        review: dict[str, object],
        event: dict[str, object],
        *,
        user_confirmed: bool | None,
    ) -> dict[str, object]:
        """Persist a review and apply it automatically only for mock evidence."""
        validate_artifact(session, "InterviewSession")
        validate_artifact(review, "Review")
        validate_artifact(event, "ProfileUpdateEvent")
        candidate_id = session.get("candidate_id")
        session_id = session.get("session_id")
        source_type = session.get("source_type")
        if not isinstance(candidate_id, str) or not isinstance(session_id, str):
            raise CandidateLockError("session requires candidate_id and session_id")
        _require_stable_id(candidate_id, "candidate")
        _require_stable_id(session_id, "session")
        self._assert_context(context, candidate_id)
        if event.get("candidate_id") != candidate_id or event.get("session_id") != session_id:
            raise CandidateLockError("review event must match locked session")
        review_version = review.get("review_version")
        if not isinstance(review_version, int) or review_version < 1:
            raise ArtifactValidationError("review_version must be a positive integer")
        if review.get("candidate_id") != candidate_id or review.get("session_id") != session_id:
            raise CandidateLockError("review must match locked session")
        if review.get("source_type") != source_type or event.get("review_version") != review_version:
            raise ArtifactValidationError("review, session, and event must have matching source and version")
        session_root = self._candidate_root(candidate_id) / "sessions" / session_id
        if not session_root.exists():
            raise FileNotFoundError("raw session must be sealed before review")
        review_path = session_root / f"review_v{review_version}.json"
        report_path = session_root / f"review_report_v{review_version}.docx"
        _json_write_immutable(review_path, review)
        if not report_path.exists():
            create_review_report(review_path, report_path)
        event_path = session_root / f"profile_update_event_v{review_version}.json"
        if source_type == "mock_interview":
            updated = self.commit_profile_event(context, event, int(event["expected_profile_version"]))
            _json_write_immutable(event_path, {**event, "state": "applied"})
            return {"state": "applied", "profile_version": updated["profile_version"], "session_root": str(session_root)}
        if source_type != "real_interview":
            raise ArtifactValidationError("review source_type must be mock_interview or real_interview")
        status_path = session_root / "review_status.json"
        if status_path.exists() and _json_read(status_path).get("state") == "rejected":
            raise ArtifactValidationError("rejected review is terminal; create a new review version")
        if user_confirmed is None:
            _json_write_atomic(status_path, {"state": "pending", "review_version": review_version})
            return {"state": "pending", "session_root": str(session_root)}
        if user_confirmed is False:
            _json_write_immutable(event_path, {**event, "state": "rejected"})
            _json_write_atomic(status_path, {"state": "rejected", "review_version": review_version})
            return {"state": "rejected", "session_root": str(session_root)}
        updated = self.commit_profile_event(context, event, int(event["expected_profile_version"]))
        _json_write_immutable(event_path, {**event, "state": "applied"})
        _json_write_atomic(status_path, {"state": "applied", "review_version": review_version})
        return {"state": "applied", "profile_version": updated["profile_version"], "session_root": str(session_root)}

    def recover(self, context: dict[str, object]) -> dict[str, object]:
        candidate_id = context.get("candidate_id")
        if not isinstance(candidate_id, str):
            raise CandidateLockError("context requires candidate_id")
        self._assert_context(context, candidate_id)
        return self.current_profile(candidate_id)


def cloud_smoke_decision(capability: object | None, candidate_id: str) -> dict[str, object]:
    """Return a truthful no-op outcome until a real cloud capability is injected."""
    if not candidate_id.startswith("TEST-"):
        raise CandidateLockError("cloud smoke candidates must use TEST- IDs")
    if capability is None:
        return {"status": "unverified", "write_requests": []}
    return {"status": "ready", "write_requests": ["requires real capability execution"]}
