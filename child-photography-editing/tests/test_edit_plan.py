import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_edit_plan import build_edit_plan, validate_edit_plan


class EditPlanTest(unittest.TestCase):
    def test_crying_background_edit_protects_expression_and_person(self):
        plan = build_edit_plan("img-1", "background-only", "lying", "crying", {"ratio": "3:5", "width": 1200, "height": 2000}, {})
        self.assertIn("entire-person", plan["protectedRegions"])
        self.assertIn("original-expression", plan["protectedRegions"])
        self.assertEqual(plan["allowedRegions"], ["background"])
        self.assertTrue(plan["preserveCrying"])

    def test_full_frame_regeneration_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "full-frame"):
            validate_edit_plan({"mode": "full-frame", "protectedRegions": [], "allowedRegions": ["entire-frame"]})

    def test_theme_edit_keeps_person_protected(self):
        plan = build_edit_plan("img-2", "theme-edit", "standing", "neutral", {"ratio": "3:5"}, {})
        self.assertIn("peripheral-elements", plan["allowedRegions"])
        self.assertIn("face", plan["forbiddenOperations"])


if __name__ == "__main__":
    unittest.main()
