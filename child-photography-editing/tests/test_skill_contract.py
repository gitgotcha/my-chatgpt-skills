from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
AGENTS = ROOT / "agents" / "openai.yaml"
EXPECTED_REFERENCES = ("workflow-contract.md", "identity-preservation.md", "style-learning.md", "edit-modes.md", "style-recipes.md", "batch-consistency.md", "qa-and-fallback.md", "prompt-templates.md")


class SkillContractTest(unittest.TestCase):
    def test_frontmatter_uses_triggering_description(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("description: Use when", text.split("---", 2)[1])

    def test_person_authenticity_hard_lock_is_complete(self):
        text = SKILL.read_text(encoding="utf-8")
        for term in ("换脸", "五官", "脸型", "头型", "眼型", "眼距", "鼻子", "嘴型", "耳朵", "发际线", "发型", "发量", "身体比例", "四肢比例", "手脚结构", "年龄感", "姿势", "动作", "原始表情"):
            self.assertIn(term, text)
        self.assertIn("人物真实性 > 用户本次明确要求 > 新参考样本 > 已肯定的处理方法", text)

    def test_core_modes_and_defaults_are_declared(self):
        text = SKILL.read_text(encoding="utf-8")
        for mode in ("background-only", "skin-only", "crop-only", "theme-edit", "poster-edit", "batch-style-transfer"):
            self.assertIn(mode, text)
        for value in ("3:5", "1200×2000", "3%–5%", "哭泣"):
            self.assertIn(value, text)

    def test_references_are_routed_and_exist(self):
        text = SKILL.read_text(encoding="utf-8")
        for name in EXPECTED_REFERENCES:
            self.assertIn(f"references/{name}", text)
            self.assertTrue((ROOT / "references" / name).is_file())

    def test_references_are_loaded_by_stage_instead_of_all_at_once(self):
        text = SKILL.read_text(encoding="utf-8")
        for stage in ("授权", "风格", "编辑规划", "批次"):
            self.assertIn(stage, text)
        self.assertNotIn("先读取并遵循：", text)

    def test_authorization_and_privacy_gate_precedes_photo_access(self):
        skill = SKILL.read_text(encoding="utf-8")
        workflow = (ROOT / "references" / "workflow-contract.md").read_text(encoding="utf-8")
        for text in (skill, workflow):
            for phrase in ("授权先于读取", "本地优先", "永不覆盖原图", "第三方", "明确告知", "明确同意", "本地元数据"):
                self.assertIn(phrase, text)
            self.assertLess(text.index("授权先于读取"), text.index("读取开发者"))

    def test_interface_describes_sample_first_batch_editing(self):
        text = AGENTS.read_text(encoding="utf-8")
        for phrase in ("儿童摄影样本学习与批量创作", "开发者参考样本", "学习", "批量", "人物真实性"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
