from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ChildPhotographyRoutingContractTest(unittest.TestCase):
    def test_new_skill_replaces_old_directory(self):
        self.assertTrue((ROOT / "child-photography-editing" / "SKILL.md").is_file())
        self.assertFalse((ROOT / "child-photoShop-skill").exists())

    def test_router_describes_sample_first_batch_workflow(self):
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn("child-photography-editing/SKILL.md", text)
        for phrase in ("开发者样本", "学习风格", "批量处理", "人物不失真"):
            self.assertIn(phrase, text)
        self.assertNotIn("child-photoShop-skill/SKILL.md", text)

    def test_readme_uses_only_the_new_skill_entry(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("child-photography-editing", text)
        self.assertNotIn("child-photoShop-skill", text)
