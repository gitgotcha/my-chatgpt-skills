"""Active persistence entrypoints must route through the single-user RDS-JBryon MCP."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RdsJBryonActiveContractTest(unittest.TestCase):
    def test_repository_instructions_use_one_path_routed_store(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("RDS-JBryon", agents)
        self.assertIn("kind=query", agents)
        self.assertIn("kind=request", agents)
        self.assertNotIn("user.resolve", agents)
        self.assertNotIn("submit_event", agents)

    def test_active_persistent_skills_link_to_the_rds_jbryon_runtime(self):
        skill_names = (
            "adaptive-study-planning",
            "algorithm-learning",
            "child-photography-editing",
            "conducting-java-backend-mock-interviews",
            "java-knowledge-based-on-resume-learn-skill",
            "profile-aware-skill-creator",
            "reviewing-java-backend-interviews",
            "software-project-learning",
        )
        for name in skill_names:
            text = (ROOT / name / "SKILL.md").read_text(encoding="utf-8")
            with self.subTest(skill=name):
                self.assertIn("rds-jbryon-runtime.md", text)
                self.assertNotIn("rds-v2-runtime.md", text)

    def test_shared_runtime_documents_path_routes_and_single_user_rule(self):
        path = ROOT / "references" / "rds-jbryon-runtime.md"
        self.assertTrue(path.is_file())
        runtime = path.read_text(encoding="utf-8")
        for required in ("project/12306", "knowledge/java/jvm", "乔炳源", "kind=query", "kind=request"):
            with self.subTest(required=required):
                self.assertIn(required, runtime)
        for forbidden in ("user.resolve", "account.register", "submit_event"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, runtime)


if __name__ == "__main__":
    unittest.main()
