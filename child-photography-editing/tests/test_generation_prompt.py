import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_generation_prompt import build_prompt


class GenerationPromptTest(unittest.TestCase):
    def test_prompt_uses_new_palette_and_methods_without_style_leakage(self):
        profile = {"styleAuthority": {"palette": ["cream", "orange"], "theme": "little-explorers"}, "approvedTreatmentHints": {"background": {"edge_cleanliness": "high"}}}
        plan = {"mode": "background-only", "allowedRegions": ["background"], "outputSpec": {"ratio": "3:5", "width": 1200, "height": 2000}}
        prompt = build_prompt(profile, plan)
        self.assertIn("cream", prompt["instruction"])
        self.assertIn("little-explorers", prompt["instruction"])
        self.assertIn("edge_cleanliness", prompt["instruction"])
        self.assertEqual(prompt["maskPolicy"], "background-only")
        self.assertIn("full-frame regeneration", prompt["negativeConstraints"])
        self.assertNotIn("old-green", prompt["instruction"])

    def test_prompt_contains_all_identity_constraints_and_crying(self):
        prompt = build_prompt({"styleAuthority": {}}, {"mode": "theme-edit", "outputSpec": {}})
        for term in ("facial features", "face shape", "head shape", "eye shape", "eye spacing", "nose", "mouth shape", "ears", "hairline", "hairstyle", "hair amount", "body proportions", "limb proportions", "hands or feet", "age", "pose", "action", "original expression", "preserve crying"):
            self.assertIn(term, prompt["negativeConstraints"])


if __name__ == "__main__":
    unittest.main()
