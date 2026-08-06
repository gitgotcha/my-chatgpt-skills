"""Pure Google Drive artifact planning; connector calls remain runtime-owned."""

from __future__ import annotations

import re


def _require_prefixed(value: str, prefix: str, name: str) -> None:
    patterns = {
        "CAND-": r"CAND-\d{8}-\d{3}",
        "RES-": r"RES-\d{8}-\d{3}",
    }
    if not isinstance(value, str) or not re.fullmatch(patterns[prefix], value):
        raise ValueError(f"{name} must be a stable {prefix} identifier")


def _require_session_id(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"(?:MOCK|REAL)-\d{8}-\d{3}", value):
        raise ValueError("session_id must be a stable MOCK- or REAL- identifier")


def build_candidate_tree_plan(
    *, root_folder_id: str, candidate_id: str, resume_id: str
) -> dict[str, object]:
    """Describe only the candidate-scoped Drive layout that a connector must create."""
    if not isinstance(root_folder_id, str) or not root_folder_id.strip():
        raise ValueError("root_folder_id must be a non-empty opaque string")
    _require_prefixed(candidate_id, "CAND-", "candidate_id")
    _require_prefixed(resume_id, "RES-", "resume_id")
    base = f"candidates/{candidate_id}"
    return {
        "provider": "google_drive_connector",
        "root_folder_id": root_folder_id,
        "candidate_id": candidate_id,
        "folders": [
            f"{base}/resumes/original",
            f"{base}/resumes/parsed",
            f"{base}/profile/history",
            f"{base}/events",
            f"{base}/sessions",
        ],
        "artifacts": [
            f"{base}/candidate.json",
            f"{base}/resumes/resume_index.json",
            f"{base}/resumes/parsed/{resume_id}_claims.json",
            f"{base}/profile/current_profile.json",
        ],
    }


def build_profile_commit_plan(
    *, candidate_id: str, session_id: str, review_version: int, expected_profile_version: int
) -> dict[str, object]:
    """Describe an optimistic, append-only event commit for runtime connector execution."""
    _require_prefixed(candidate_id, "CAND-", "candidate_id")
    _require_session_id(session_id)
    if review_version < 1 or expected_profile_version < 0:
        raise ValueError("versions must be non-negative and review_version must be positive")
    return {
        "candidate_id": candidate_id,
        "application_key": f"{candidate_id}|{session_id}|{review_version}",
        "preconditions": {"expected_profile_version": expected_profile_version},
        "immutable_artifacts": [
            f"sessions/{session_id}/review_v{review_version}.json",
            f"sessions/{session_id}/profile_update_event_v{review_version}.json",
            f"profile/history/profile_v{expected_profile_version}.json",
        ],
        "mutable_pointer": "profile/current_profile.json",
        "connector_sequence": [
            "read current_profile.json and verify expected version",
            "write immutable review and event artifacts",
            "write immutable profile history snapshot",
            "write validated replacement current_profile.json last",
        ],
    }
