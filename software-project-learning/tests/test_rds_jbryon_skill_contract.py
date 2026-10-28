from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MOCK = ROOT.parent / "conducting-java-backend-mock-interviews"
PROJECT_SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")
LESSON = (ROOT / "references" / "detailed-lesson-format.md").read_text(encoding="utf-8")
RDS = (ROOT / "references" / "rds-jbryon-runtime.md").read_text(encoding="utf-8")
MOCK_SKILL = (MOCK / "SKILL.md").read_text(encoding="utf-8")
MOCK_TARGET = (MOCK / "references" / "project-targeted-interview.md").read_text(encoding="utf-8")


class RdsJbryonSkillContractTests(unittest.TestCase):
    def test_projects_use_readable_routes_and_not_account_identity(self):
        self.assertIn("project-12306", PROJECT_SKILL)
        self.assertIn("project/12306", RDS)
        self.assertIn("knowledge/java/jvm", RDS)
        self.assertIn("用户无需提供任何内部标识", RDS)
        for text in (PROJECT_SKILL, MOCK_SKILL):
            for forbidden in ("user.resolve", "account.register", "submit_event(interview.session.completed)"):
                self.assertNotIn(forbidden, text)

    def test_learning_and_mock_share_snapshot_and_recap_is_not_persisted(self):
        self.assertIn("共用此契约", RDS)
        self.assertIn("回顾本身不追加", RDS)
        self.assertIn("用户首次原答", RDS)
        self.assertIn("原答不可被润色稿替换", MOCK_SKILL)
        self.assertIn("学习快照.json", MOCK_TARGET)

    def test_confirmed_routes_are_provisioned_automatically_but_read_only_never_writes(self):
        self.assertIn("自动补齐", RDS)
        self.assertIn("directory.list", RDS)
        self.assertIn("snapshot.create", RDS)
        self.assertIn("只读", RDS)
        self.assertIn("新顶层领域", RDS)

    def test_diagram_and_code_teaching_are_source_grounded(self):
        self.assertIn("sequenceDiagram", PROJECT_SKILL)
        self.assertIn("逐行", LESSON)
        self.assertIn("源码", LESSON)
        self.assertIn("幽默", PROJECT_SKILL)

    def test_mock_is_byte_dance_campus_level_and_source_sourced(self):
        self.assertIn("字节跳动校招 Java 后端", MOCK_SKILL)
        self.assertIn("近期公开面经", MOCK_SKILL)
        self.assertIn("技术答案以", MOCK_SKILL)
        self.assertIn("一次只问一道主问题", MOCK_SKILL)


if __name__ == "__main__":
    unittest.main()
