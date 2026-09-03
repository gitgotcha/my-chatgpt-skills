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

    def test_every_mode_requires_its_exact_allowed_regions(self):
        cases = {
            "background-only": ["face"],
            "skin-only": ["skin-tone-adjustments", "face"],
            "crop-only": ["crop-canvas", "background"],
            "theme-edit": ["background", "peripheral-elements"],
            "poster-edit": ["entire-frame"],
            "batch-style-transfer": ["background", "peripheral-elements", "safe-text-zones", "face"],
        }
        for mode, unsafe_regions in cases.items():
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, "allowed regions"):
                validate_edit_plan(
                    {
                        "mode": mode,
                        "protectedRegions": ["entire-person", "original-expression"],
                        "allowedRegions": unsafe_regions,
                        "forbiddenOperations": [
                            "face", "facial-features", "head-shape", "eyes", "eye-spacing", "nose", "mouth", "ears",
                            "hairline", "hair", "body-proportions", "limb-proportions", "hands-feet", "age", "pose", "action", "original-expression",
                        ],
                        "requestedChanges": {},
                        "outputSpec": {},
                    }
                )

    def test_missing_required_protection_is_rejected(self):
        plan = build_edit_plan("img-3", "background-only", "sitting", "neutral", {}, {})
        plan["protectedRegions"].remove("original-expression")
        with self.assertRaisesRegex(ValueError, "protected regions"):
            validate_edit_plan(plan)

    def test_person_mutating_and_unknown_requested_changes_are_rejected(self):
        for changes in (
            {"replaceFace": True},
            {"background": "cream", "surprise": "cowboy-hat"},
            {"background": {"replaceFace": True}},
        ):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "requestedChanges"):
                build_edit_plan("img-4", "background-only", "standing", "neutral", {}, changes)

    def test_malformed_region_and_operation_collections_are_rejected_cleanly(self):
        plan = build_edit_plan("img-4b", "background-only", "standing", "neutral", {}, {})
        for field, value in (("protectedRegions", {}), ("forbiddenOperations", ["face", {}])):
            malformed = dict(plan)
            malformed[field] = value
            with self.subTest(field=field):
                try:
                    validate_edit_plan(malformed)
                except TypeError as exc:
                    self.fail(f"malformed {field} leaked TypeError: {exc}")
                except ValueError:
                    pass
                else:
                    self.fail(f"malformed {field} was accepted")

    def test_requested_changes_are_limited_by_mode(self):
        with self.assertRaisesRegex(ValueError, "requestedChanges"):
            build_edit_plan("img-5", "skin-only", "standing", "neutral", {}, {"background": "cream"})

    def test_empty_output_spec_is_normalized_before_storage(self):
        plan = build_edit_plan("img-6", "poster-edit", "standing", "neutral", {}, {})
        expected = {"ratio": "3:5", "width": 1200, "height": 2000}
        self.assertEqual(plan["outputSpec"], expected)
        self.assertEqual(plan["crop"], expected)


if __name__ == "__main__":
    unittest.main()
