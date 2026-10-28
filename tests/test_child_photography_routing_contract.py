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

    def test_readme_child_photo_section_matches_the_actual_skill(self):
        text = (ROOT / "child-photography-editing" / "SKILL.md").read_text(encoding="utf-8")
        section = text
        for mode in ("background-only", "skin-only", "crop-only", "theme-edit", "poster-edit", "batch-style-transfer"):
            self.assertIn(mode, section)
        for capability in ("Style Profile", "Approved Treatment Hints", "Edit Plan", "Batch Style Lock", "QA"):
            self.assertIn(capability, section)
        # The skill may mention excluded activities in its boundary statement;
        # assert it does not claim to implement those workflows.
        for stale_workflow in ("Contact Sheet generator", "风格库原型功能", "自动选片流程"):
            self.assertNotIn(stale_workflow, section)
        self.assertIn("绝对人物锁定", section)
        self.assertIn("child-photography-editing", section)
        self.assertTrue((ROOT / "child-photography-editing" / "SKILL.md").is_file())
