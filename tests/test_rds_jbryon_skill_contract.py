"""Repository-level contract for the path-routed RDS-JBryon Skills."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RdsJBryonSkillContractTest(unittest.TestCase):
    def test_project_and_mock_interview_share_the_project_snapshot_route(self):
        project = (ROOT / "software-project-learning/SKILL.md").read_text(encoding="utf-8")
        interview = (ROOT / "conducting-java-backend-mock-interviews/SKILL.md").read_text(encoding="utf-8")
        runtime = (ROOT / "software-project-learning/references/rds-jbryon-runtime.md").read_text(encoding="utf-8")
        self.assertIn("project/12306", project + interview + runtime)
        self.assertIn("学习快照.json", runtime)
        self.assertIn("原答", interview)

    def test_project_route_does_not_require_internal_identity(self):
        runtime = (ROOT / "software-project-learning/references/rds-jbryon-runtime.md").read_text(encoding="utf-8")
        self.assertIn("用户无需提供任何内部标识", runtime)

    def test_all_active_profile_skills_have_path_based_storage_guidance(self):
        for skill in (
            "algorithm-learning",
            "adaptive-study-planning",
            "child-photography-editing",
            "java-knowledge-based-on-resume-learn-skill",
            "profile-aware-skill-creator",
            "reviewing-java-backend-interviews",
        ):
            text = (ROOT / skill / "SKILL.md").read_text(encoding="utf-8")
            with self.subTest(skill=skill):
                self.assertIn("RDS-JBryon", text)
                self.assertIn("rds", text)


if __name__ == "__main__":
    unittest.main()
