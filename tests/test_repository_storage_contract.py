"""Repository-wide active persistence contract for RDS-JBryon."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = (
    "adaptive-study-planning",
    "algorithm-learning",
    "child-photography-editing",
    "conducting-java-backend-mock-interviews",
    "java-knowledge-based-on-resume-learn-skill",
    "profile-aware-skill-creator",
    "reviewing-java-backend-interviews",
    "software-project-learning",
)


class RepositoryStorageContractTest(unittest.TestCase):
    def test_shared_contract_is_single_user_and_path_routed(self):
        text = (ROOT / "references/rds-jbryon-runtime.md").read_text(encoding="utf-8")
        for token in ("乔炳源", "project/12306", "knowledge/java/jvm", "kind=query", "kind=request"):
            with self.subTest(token=token):
                self.assertIn(token, text)
        for retired in ("user.resolve", "account.register", "submit_event"):
            with self.subTest(retired=retired):
                self.assertNotIn(retired, text)

    def test_every_persistent_skill_uses_the_new_runtime(self):
        for skill in SKILLS:
            text = (ROOT / skill / "SKILL.md").read_text(encoding="utf-8")
            with self.subTest(skill=skill):
                self.assertIn("RDS-JBryon", text)
                self.assertNotIn("rds-v2-runtime.md", text)

    def test_repository_router_has_no_legacy_write_route(self):
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("RDS-JBryon", text)
        self.assertNotIn("submit_event", text)
        self.assertNotIn("user.resolve", text)

    def test_legacy_worker_and_mcp_source_files_are_removed(self):
        for path in ("services/reliable-drive-sync-worker", "tools/reliable-drive-sync-mcp", "cloud-mcp"):
            with self.subTest(path=path):
                target = ROOT / path
                self.assertFalse(
                    target.exists() and any(child.is_file() for child in target.rglob("*"))
                )


if __name__ == "__main__":
    unittest.main()
