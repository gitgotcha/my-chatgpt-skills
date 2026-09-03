import sys
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_generation_prompt import build_prompt
from validate_edit_plan import build_edit_plan


class GenerationPromptTest(unittest.TestCase):
    def test_prompt_uses_new_palette_and_methods_without_style_leakage(self):
        profile = {"styleAuthority": {"palette": ["cream", "orange"], "theme": "little-explorers"}, "approvedTreatmentHints": {"background": {"edge_cleanliness": "high"}}}
        plan = build_edit_plan("img-0", "background-only", "standing", "neutral", {}, {})
        prompt = build_prompt(profile, plan)
        self.assertIn("cream", prompt["instruction"])
        self.assertIn("little-explorers", prompt["instruction"])
        self.assertIn("edge_cleanliness", prompt["instruction"])
        self.assertEqual(prompt["maskPolicy"], "background-only")
        self.assertIn("full-frame regeneration", prompt["negativeConstraints"])
        self.assertNotIn("old-green", prompt["instruction"])

    def test_prompt_contains_all_identity_constraints_and_crying(self):
        plan = build_edit_plan("img-1", "theme-edit", "standing", "neutral", {}, {})
        prompt = build_prompt({"styleAuthority": {}}, plan)
        for term in ("facial features", "face shape", "head shape", "eye shape", "eye spacing", "nose", "mouth shape", "ears", "hairline", "hairstyle", "hair amount", "body proportions", "limb proportions", "hands or feet", "age", "pose", "action", "original expression", "preserve crying"):
            self.assertIn(term, prompt["negativeConstraints"])

    def test_prompt_revalidates_a_handcrafted_unsafe_plan(self):
        plan = build_edit_plan("img-2", "theme-edit", "standing", "neutral", {}, {})
        unsafe = deepcopy(plan)
        unsafe["allowedRegions"] = ["entire-frame"]
        with self.assertRaisesRegex(ValueError, "allowed regions"):
            build_prompt({"styleAuthority": {}}, unsafe)

    def test_prompt_rejects_unvalidated_treatment_hint_leakage(self):
        plan = build_edit_plan("img-2b", "background-only", "standing", "neutral", {}, {})
        profile = {"styleAuthority": {}, "approvedTreatmentHints": {"background": {"edge_cleanliness": "old-green"}}}
        with self.assertRaisesRegex(ValueError, "invalid treatment value"):
            build_prompt(profile, plan)

    def test_prompt_receives_normalized_output_spec(self):
        plan = build_edit_plan("img-3", "crop-only", "standing", "neutral", {}, {})
        self.assertEqual(
            build_prompt({"styleAuthority": {}}, plan)["outputSpec"],
            {"ratio": "3:5", "width": 1200, "height": 2000},
        )


if __name__ == "__main__":
    unittest.main()
