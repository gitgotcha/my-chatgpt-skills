import inspect
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from style_profile import ALLOWED_HINTS, compile_style_profile, validate_approved_hints


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

    def test_approved_hint_values_cannot_carry_old_style_tokens(self):
        for hints in (
            {"background": {"edge_cleanliness": "old-green"}},
            {"elements": {"density": "cowboy-hat"}},
        ):
            with self.subTest(hints=hints), self.assertRaisesRegex(ValueError, "invalid treatment value"):
                validate_approved_hints(hints)

    def test_every_approved_hint_field_rejects_arbitrary_strings(self):
        for section, fields in ALLOWED_HINTS.items():
            for field in fields:
                with self.subTest(section=section, field=field), self.assertRaisesRegex(ValueError, "invalid treatment value"):
                    validate_approved_hints({section: {field: "old-style-token"}})

    def test_approved_hint_schemas_reject_malformed_and_non_finite_values_cleanly(self):
        for hints in (
            {"background": {"edge_cleanliness": {"quality": "high"}}},
            {"skin": {"brightness_delta_percent": float("nan")}},
        ):
            with self.subTest(hints=hints):
                try:
                    validate_approved_hints(hints)
                except TypeError as exc:
                    self.fail(f"malformed hint leaked TypeError: {exc}")
                except ValueError as exc:
                    self.assertIn("invalid treatment value", str(exc))
                else:
                    self.fail("malformed hint was accepted")

    def test_every_style_dimension_records_active_evidence(self):
        self.assertIn("inferences", inspect.signature(compile_style_profile).parameters)
        profile = compile_style_profile(
            observations={
                "palette": {"value": ["cream", "orange"], "source": "developer-reference-1", "confidence": 0.95},
                "lighting": "soft",
            },
            inferences={"theme": {"value": "little-explorers", "source": "reference-analysis", "confidence": 0.65}},
            overrides={"lighting": {"value": "warm", "source": "current request", "confidence": 1}},
            approved_hints={},
        )
        self.assertEqual(profile["styleAuthority"], {"palette": ["cream", "orange"], "lighting": "warm", "theme": "little-explorers"})
        self.assertEqual(profile["styleEvidence"]["palette"], {"kind": "observed", "source": "developer-reference-1", "confidence": 0.95})
        self.assertEqual(profile["styleEvidence"]["theme"], {"kind": "inferred", "source": "reference-analysis", "confidence": 0.65})
        self.assertEqual(profile["styleEvidence"]["lighting"], {"kind": "user-override", "source": "current request", "confidence": 1.0})

    def test_inference_never_overrides_current_user_override(self):
        self.assertIn("inferences", inspect.signature(compile_style_profile).parameters)
        profile = compile_style_profile(
            observations={},
            inferences={"theme": "cowboy"},
            overrides={"theme": "cream-studio"},
            approved_hints={},
        )
        self.assertEqual(profile["styleAuthority"]["theme"], "cream-studio")
        self.assertEqual(profile["styleEvidence"]["theme"]["kind"], "user-override")

    def test_invalid_evidence_confidence_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "confidence"):
            compile_style_profile(
                observations={"palette": {"value": ["cream"], "source": "reference", "confidence": 1.1}},
                overrides={},
                approved_hints={},
            )


if __name__ == "__main__":
    unittest.main()
