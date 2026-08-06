from __future__ import annotations

import unittest

from scripts.drive_protocol import build_candidate_tree_plan, build_profile_commit_plan


class DriveProtocolTests(unittest.TestCase):
    def test_candidate_tree_is_locked_to_one_candidate_and_expected_paths(self) -> None:
        plan = build_candidate_tree_plan(
            root_folder_id="root-id",
            candidate_id="CAND-20260806-001",
            resume_id="RES-20260806-001",
        )

        self.assertEqual(plan["candidate_id"], "CAND-20260806-001")
        self.assertEqual(
            plan["folders"],
            [
                "candidates/CAND-20260806-001/resumes/original",
                "candidates/CAND-20260806-001/resumes/parsed",
                "candidates/CAND-20260806-001/profile/history",
                "candidates/CAND-20260806-001/events",
                "candidates/CAND-20260806-001/sessions",
            ],
        )
        self.assertIn(
            "candidates/CAND-20260806-001/resumes/parsed/RES-20260806-001_claims.json",
            plan["artifacts"],
        )

    def test_profile_commit_requires_expected_version_and_never_overwrites_history(self) -> None:
        plan = build_profile_commit_plan(
            candidate_id="CAND-20260806-001",
            session_id="MOCK-20260806-001",
            review_version=1,
            expected_profile_version=3,
        )

        self.assertEqual(plan["application_key"], "CAND-20260806-001|MOCK-20260806-001|1")
        self.assertEqual(plan["preconditions"], {"expected_profile_version": 3})
        self.assertEqual(plan["immutable_artifacts"], [
            "sessions/MOCK-20260806-001/review_v1.json",
            "sessions/MOCK-20260806-001/profile_update_event_v1.json",
            "profile/history/profile_v3.json",
        ])
        self.assertEqual(plan["mutable_pointer"], "profile/current_profile.json")

    def test_drive_plan_rejects_path_like_identifiers(self) -> None:
        with self.assertRaises(ValueError):
            build_candidate_tree_plan(
                root_folder_id=["root"],  # type: ignore[arg-type]
                candidate_id="CAND-20260806-001",
                resume_id="RES-20260806-001",
            )
        with self.assertRaises(ValueError):
            build_candidate_tree_plan(
                root_folder_id="root-id",
                candidate_id="CAND-20260806-001/../OTHER",
                resume_id="RES-20260806-001",
            )
        with self.assertRaises(ValueError):
            build_candidate_tree_plan(
                root_folder_id="root-id",
                candidate_id="CAND-20260806-001",
                resume_id="RES-20260806-001\\other",
            )
        with self.assertRaises(ValueError):
            build_profile_commit_plan(
                candidate_id="CAND-20260806-001",
                session_id="MOCK-20260806-001/../../other",
                review_version=1,
                expected_profile_version=0,
            )
