from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReviewModelRoutingReadmeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")

    def test_overview_lists_eight_skills_and_new_entry(self):
        self.assertIn("目前仓库包含 8 个主要 Skill", self.readme)
        self.assertIn("[review-model-routing](./review-model-routing/)", self.readme)

    def test_dedicated_section_describes_plan_time_behavior(self):
        section = self.readme.split("# 6.1 Review Model Routing", 1)[1].split(
            "# 7. Reliable Drive Sync", 1
        )[0]
        for phrase in ("执行计划", "具体模型", "实施前", "实施后", "放行条件"):
            self.assertIn(phrase, section)
        self.assertIn("./review-model-routing/SKILL.md", section)

    def test_quick_navigation_links_the_skill(self):
        quick = self.readme.split("# 23. 快速导航", 1)[1]
        self.assertIn("Review Model Routing", quick)
        self.assertIn("./review-model-routing/", quick)


if __name__ == "__main__":
    unittest.main()
