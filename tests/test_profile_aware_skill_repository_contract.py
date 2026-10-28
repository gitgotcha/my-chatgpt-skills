"""The Skill creator and repository router describe the active RDS-JBryon route."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProfileAwareSkillRepositoryContractTest(unittest.TestCase):
    def test_router_keeps_profile_aware_skill_creation_explicit(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("profile-aware-skill-creator/SKILL.md", agents)
        self.assertIn("显式调用", agents)

    def test_skill_creator_generates_readable_snapshot_routes(self):
        skill = (ROOT / "profile-aware-skill-creator/SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references/rds-jbryon-runtime.md").read_text(encoding="utf-8")
        self.assertIn("RDS-JBryon", skill)
        self.assertIn("用户可读路径", skill)
        self.assertIn("knowledge/java/jvm", contract)
        self.assertNotIn("submit_event", skill)

    def test_local_review_artifacts_are_not_account_scoped(self):
        review = (ROOT / "reviewing-java-backend-interviews/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("outputs/interview/<sessionId>/", review)
        self.assertNotIn("outputs/interview/<userId>/", review)


if __name__ == "__main__":
    unittest.main()
