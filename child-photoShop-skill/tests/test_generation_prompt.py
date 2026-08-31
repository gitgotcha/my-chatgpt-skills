"""Tests for the generation-prompt compiler.

The compiler is the bridge between "what we measured" and "what a generative
backend does". It is dangerous in a specific way: a prompt that forgets a
prohibition produces a plausible-looking photograph of a different child. So
the tests here are mostly about what must ALWAYS be present, not about the
wording being pretty.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_generation_prompt as gp  # noqa: E402
import fixtures  # noqa: E402
import style_profile as sp  # noqa: E402

WARM = {
    "exposure": {
        "mean_luma": 0.66,
        "median_luma": 0.68,
        "contrast": 0.18,
        "shadow_lift": 0.33,
        "highlight_rolloff": 0.92,
    },
    "white_balance": {"r_gain": 0.88, "b_gain": 1.14, "temperature_hint": "warm"},
    "color": {"mean_saturation": 0.44, "dominant_hues": [30, 40, 200], "palette": []},
    "skin": {"tone_hex": "#e8c39a", "target_luma": 0.74, "warmth": 18.0, "saturation": 0.3},
    "background": {"tone_hex": "#6b4f3a", "vignette": 0.03},
    "lighting": {"direction": "left", "softness": 0.7, "shadow_depth": 0.2},
    "texture": {"grain": 0.03, "microcontrast": 0.4, "halation": 0.3},
    "mood": [],
}

COOL = dict(
    WARM,
    white_balance={"r_gain": 1.15, "b_gain": 0.87, "temperature_hint": "cool"},
    exposure=dict(WARM["exposure"], mean_luma=0.38, contrast=0.27),
    lighting={"direction": "top", "softness": 0.2, "shadow_depth": 0.4},
)


class CompileTests(unittest.TestCase):
    def test_every_mode_returns_the_same_shape(self):
        for mode in gp.MODES:
            result = gp.build_prompt(WARM, mode=mode)
            self.assertEqual(result["mode"], mode)
            for key in ("positive", "negative", "params", "verify", "privacy", "mode_note"):
                self.assertIn(key, result, "missing key {} in mode {}".format(key, mode))

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            gp.build_prompt(WARM, mode="make_it_pretty")

    def test_compilation_is_deterministic(self):
        """The same profile must always yield the same prompt.

        Batches are generated from one profile; if the wording drifts between
        calls, the batch stops matching.
        """
        self.assertEqual(gp.build_prompt(WARM), gp.build_prompt(WARM))

    def test_positive_prompt_is_not_empty(self):
        result = gp.build_prompt(WARM)
        self.assertGreaterEqual(len(result["positive"]), 6)


class NegativeTests(unittest.TestCase):
    """The prohibitions are the whole point of this script."""

    REQUIRED = (
        "changed face shape",
        "different child",
        "aged-up face",
        "adult facial structure",
        "slimmer face",
        "enlarged eyes",
        "eye corner opening",
        "reshaped nose",
        "plumped lips",
        "changed hairstyle or hairline",
        "adult makeup",
        "contouring",
        "extra fingers",
        "deformed hands",
        "plastic waxy skin",
        "over-smoothed skin",
    )

    def test_every_mode_carries_the_full_negative_list(self):
        for mode in gp.MODES:
            negatives = gp.build_prompt(WARM, mode=mode)["negative"]
            for phrase in self.REQUIRED:
                self.assertIn(phrase, negatives, "{} missing in mode {}".format(phrase, mode))

    def test_expression_lock_is_in_the_negatives(self):
        negatives = gp.build_prompt(WARM)["negative"]
        for phrase in ("standardised grin", "posed smile replacing the real expression"):
            self.assertIn(phrase, negatives)

    def test_negatives_are_not_derived_from_the_profile(self):
        """A profile must never be able to shorten the prohibition list.

        The negatives are a floor. If they were computed from the measurements
        then a profile could, in principle, talk its way out of them.
        """
        self.assertEqual(gp.build_prompt(WARM)["negative"], gp.build_prompt(COOL)["negative"])
        self.assertEqual(gp.build_prompt({})["negative"], gp.build_prompt(WARM)["negative"])

    def test_no_duplicate_negatives(self):
        negatives = gp.build_prompt(WARM)["negative"]
        self.assertEqual(len(negatives), len(set(negatives)))


class ProfileToWordsTests(unittest.TestCase):
    def test_warm_and_cool_profiles_produce_different_light_and_colour(self):
        warm_text = " ".join(gp.build_prompt(WARM)["positive"])
        cool_text = " ".join(gp.build_prompt(COOL)["positive"])
        self.assertIn("warm amber", warm_text)
        self.assertIn("cool blue-teal", cool_text)
        self.assertIn("bright airy", warm_text)
        self.assertIn("low-key", cool_text)

    def test_softness_changes_the_light_wording(self):
        soft = " ".join(gp.lighting_words(WARM))
        hard = " ".join(gp.lighting_words(COOL))
        self.assertIn("soft", soft)
        self.assertIn("directional", hard)

    def test_grain_is_mentioned_only_when_measured(self):
        grainy = " ".join(gp.texture_words(WARM))
        clean = " ".join(gp.texture_words({"texture": {"grain": 0.0, "microcontrast": 0.1, "halation": 0.0}}))
        self.assertIn("film grain", grainy)
        self.assertIn("grain-free", clean)

    def test_dominant_hues_are_named(self):
        text = " ".join(gp.color_words(WARM))
        self.assertIn("orange", text)

    def test_skin_hex_is_carried_into_the_prompt(self):
        text = " ".join(gp.color_words(WARM))
        self.assertIn("#e8c39a", text)


class ModeTests(unittest.TestCase):
    def test_background_only_protects_the_child_in_the_positive_prompt(self):
        text = " ".join(gp.build_prompt(WARM, mode="background_only")["positive"])
        self.assertIn("background only", text)
        self.assertIn("exactly as photographed", text)

    def test_background_only_sets_a_mask_and_a_low_strength(self):
        params = gp.build_prompt(WARM, mode="background_only")["params"]
        self.assertIn("child", params["mask"])
        self.assertLessEqual(params["max_strength"], 0.45)

    def test_full_frame_stays_weak_and_says_it_is_out_of_scope(self):
        result = gp.build_prompt(WARM, mode="full_frame")
        self.assertLessEqual(result["params"]["max_strength"], 0.35)
        self.assertIn("FULL REGENERATION", result["mode_note"])
        self.assertIn("Creative Edit Mode", result["mode_note"])

    def test_reference_board_needs_no_person(self):
        text = " ".join(gp.build_prompt(WARM, mode="reference_board")["positive"])
        self.assertIn("no person required", text)


class PrivacyTests(unittest.TestCase):
    def test_reference_board_uploads_nothing(self):
        self.assertIn("no photograph is uploaded", gp.build_prompt(WARM)["privacy"])

    def test_photo_modes_demand_consent(self):
        for mode in ("background_only", "full_frame"):
            privacy = gp.build_prompt(WARM, mode=mode)["privacy"]
            self.assertIn("explicit user consent", privacy)
            self.assertIn("section 15", privacy)


class IntentTests(unittest.TestCase):
    def test_known_instructions_map_to_wording(self):
        text = " ".join(gp.build_prompt(WARM, intent="再暖一点")["positive"])
        self.assertIn("warmer", text)

    def test_unknown_instruction_is_passed_through_not_dropped(self):
        text = " ".join(gp.build_prompt(WARM, intent="把背景换成星空")["positive"])
        self.assertIn("把背景换成星空", text)

    def test_empty_intent_adds_nothing(self):
        self.assertEqual(gp.build_prompt(WARM, intent="")["positive"], gp.build_prompt(WARM)["positive"])


class DiffTests(unittest.TestCase):
    def test_adjust_rows_become_directions(self):
        rows = [
            {"dimension": "exposure.mean_luma", "delta": 0.09, "action": "adjust"},
            {"dimension": "color.mean_saturation", "delta": -0.05, "action": "adjust"},
        ]
        words = gp.diff_words(rows)
        self.assertIn("still needs more mean luma", words)
        self.assertIn("still needs less mean saturation", words)

    def test_skip_rows_are_ignored(self):
        rows = [{"dimension": "exposure.contrast", "delta": 0.4, "action": "skip"}]
        self.assertEqual(gp.diff_words(rows), [])

    def test_diff_feeds_the_positive_prompt(self):
        rows = [{"dimension": "exposure.mean_luma", "delta": 0.09, "action": "adjust"}]
        text = " ".join(gp.build_prompt(WARM, diff=rows)["positive"])
        self.assertIn("still needs more mean luma", text)


class RobustnessTests(unittest.TestCase):
    def test_an_empty_profile_does_not_crash(self):
        result = gp.build_prompt({})
        self.assertTrue(result["positive"])
        self.assertTrue(result["negative"])

    def test_a_profile_of_garbage_types_does_not_crash(self):
        junk = {"exposure": "not a dict", "lighting": None, "color": {"dominant_hues": "nope"}}
        result = gp.build_prompt(junk)
        self.assertTrue(result["positive"])


class CliTests(unittest.TestCase):
    """The CLI is how an agent actually calls this."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = cls._tmp.name
        cls.reference = fixtures.build_warm_reference(os.path.join(cls.tmp, "reference.jpg"))
        cls.profile_path = os.path.join(cls.tmp, "profile.json")
        sp.main(
            [
                "learn",
                cls.reference,
                "--name",
                "camping",
                "--role",
                "color",
                "--out",
                cls.profile_path,
            ]
        )

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_cli_writes_markdown_to_a_file(self):
        out = os.path.join(self.tmp, "prompt.md")
        code = gp.main(["--profile", self.profile_path, "--mode", "background_only", "--out", out])
        self.assertEqual(code, 0)
        text = Path(out).read_text(encoding="utf-8")
        self.assertIn("## Negative", text)
        self.assertIn("## Verify after generation", text)

    def test_cli_emits_parseable_json(self):
        out = os.path.join(self.tmp, "prompt.json")
        code = gp.main(["--profile", self.profile_path, "--json", "--out", out])
        self.assertEqual(code, 0)
        payload = json.loads(Path(out).read_text(encoding="utf-8"))
        self.assertIn("positive", payload)
        self.assertIn("negative", payload)

    def test_cli_rejects_a_diff_that_is_not_a_list(self):
        bad = os.path.join(self.tmp, "bad.json")
        Path(bad).write_text(json.dumps({"dimension": "x"}), encoding="utf-8")
        self.assertEqual(gp.main(["--profile", self.profile_path, "--diff", bad]), 2)

    def test_end_to_end_learn_compare_then_compile(self):
        target = fixtures.build_cool_target(os.path.join(self.tmp, "target.jpg"))
        diff_path = os.path.join(self.tmp, "diff.json")
        sp.main(["compare", target, "--profile", self.profile_path, "--json"])

        rows = sp.compare_profile(target, json.loads(Path(self.profile_path).read_text(encoding="utf-8")))
        Path(diff_path).write_text(json.dumps(rows), encoding="utf-8")

        result = gp.build_prompt(
            json.loads(Path(self.profile_path).read_text(encoding="utf-8")),
            mode="background_only",
            diff=rows,
        )
        self.assertTrue(result["positive"])
        # A real compare always reports at least one off dimension on the
        # cool fixture, and every one of them must show up as a direction.
        self.assertTrue(any("still needs" in w for w in result["positive"]))


if __name__ == "__main__":
    unittest.main()
