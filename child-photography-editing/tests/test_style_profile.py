import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from style_profile import compile_style_profile, validate_approved_hints


class StyleProfileTest(unittest.TestCase):
    def test_new_reference_owns_style_while_old_approval_keeps_method_only(self):
        profile = compile_style_profile(
            observations={"palette": ["cream", "orange"], "theme": "little-explorers"},
            overrides={},
            approved_hints={"skin": {"brightness_delta_percent": 4}, "elements": {"subject_avoidance": "strict"}},
        )
        self.assertEqual(profile["styleAuthority"]["palette"], ["cream", "orange"])
        self.assertEqual(profile["styleAuthority"]["theme"], "little-explorers")
        self.assertEqual(profile["approvedTreatmentHints"]["skin"]["brightness_delta_percent"], 4)

    def test_style_bearing_values_are_rejected_from_approved_hints(self):
        with self.assertRaisesRegex(ValueError, "style-bearing"):
            validate_approved_hints({"background": {"color": "old-green"}})

    def test_skin_limits_are_clamped(self):
        profile = compile_style_profile({}, {}, {"skin": {"brightness_delta_percent": 20, "eye_refresh": "strong"}})
        self.assertEqual(profile["approvedTreatmentHints"]["skin"]["brightness_delta_percent"], 5)
        self.assertEqual(profile["approvedTreatmentHints"]["skin"]["eye_refresh"], "subtle")


if __name__ == "__main__":
    unittest.main()
