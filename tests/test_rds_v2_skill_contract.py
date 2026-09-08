"""Cross-skill contract for the Reliable Drive Sync V2 runtime."""

from __future__ import annotations

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PROFILE_AWARE_SKILLS = (
    "algorithm-learning",
    "software-project-learning",
    "child-photography-editing",
    "conducting-java-backend-mock-interviews",
    "profile-aware-skill-creator",
    "reviewing-java-backend-interviews",
)


class RdsV2SkillContractTest(unittest.TestCase):
    def test_profile_aware_skills_publish_one_shared_v2_runtime(self) -> None:
        runtime_texts = []
        for skill_name in PROFILE_AWARE_SKILLS:
            with self.subTest(skill=skill_name):
                skill_root = REPO_ROOT / skill_name
                skill_text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
                runtime_path = skill_root / "references" / "rds-v2-runtime.md"
                self.assertIn("references/rds-v2-runtime.md", skill_text)
                self.assertTrue(runtime_path.is_file())
                runtime_texts.append(runtime_path.read_text(encoding="utf-8"))

        self.assertEqual(1, len(set(runtime_texts)))

    def test_runtime_uses_v2_identity_projection_receipt_and_status_operations(self) -> None:
        runtime = (
            REPO_ROOT / "algorithm-learning" / "references" / "rds-v2-runtime.md"
        ).read_text(encoding="utf-8")
        for required in (
            '"storageVersion":2',
            '"operation":"capabilities"',
            '"operation":"user.resolve"',
            '"operation":"projection.read"',
            '"operation":"event.status"',
            '"d1_committed"',
            "projection=projected",
            "archive=archived",
        ):
            with self.subTest(required=required):
                self.assertIn(required, runtime)

        self.assertIn("不要提交 `system.user-registered`", runtime)
        self.assertIn("不从 Drive 扫描历史", runtime)

    def test_project_learning_preserves_existing_profile_domain(self) -> None:
        skill = (REPO_ROOT / "software-project-learning" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("profile/backend-project-learning", skill)
        self.assertIn("profile.evidence.recorded", skill)


if __name__ == "__main__":
    unittest.main()
