"""Behavioural tests for the core business: learn a template style, apply it.

These are the tests that would catch a regression in the thing the skill is
actually for. Contract tests only prove the documents still say the right
words; these prove the numbers still move in the right direction.

Everything runs on synthetic fixtures -- a public repo must never ship real
photographs of real children.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import apply_style  # noqa: E402
import fixtures  # noqa: E402
import style_profile as sp  # noqa: E402


def load(path):
    return sp.load_rgb(str(path))


def profile_of(rgb):
    return sp._single_profile(sp.downscale(rgb))


class StyleFixtures(unittest.TestCase):
    """Builds the fixture set once for the whole module."""

    tmp: str
    reference: str
    target: str
    profile: dict

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = cls._tmp.name
        cls.reference = fixtures.build_warm_reference(
            os.path.join(cls.tmp, "reference.jpg")
        )
        cls.target = fixtures.build_cool_target(os.path.join(cls.tmp, "target.jpg"))
        cls.profile = sp.compute_profile([cls.reference], name="camping", role="color")
        cls.ref_rgb = load(cls.reference)
        cls.tgt_rgb = load(cls.target)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def styled(self, strength=0.8, role="color"):
        return apply_style.apply_style(self.tgt_rgb, self.profile, strength, role)


# --------------------------------------------------------------------------
# the profile itself
# --------------------------------------------------------------------------


class ProfileSchemaTests(StyleFixtures):
    def test_profile_carries_every_documented_section(self):
        for section in (
            "exposure",
            "white_balance",
            "color",
            "skin",
            "background",
            "lighting",
            "texture",
            "constraints",
        ):
            self.assertIn(section, self.profile, "missing section: " + section)

    def test_profile_declares_its_schema_version_and_source(self):
        self.assertEqual(self.profile["schemaVersion"], "1.0")
        self.assertEqual(self.profile["source"]["role"], "color")
        self.assertEqual(self.profile["source"]["generator"], "child-photoShop-skill/style_profile.py")

    def test_constraints_default_to_locked_on(self):
        c = self.profile["constraints"]
        self.assertTrue(c["identity_lock"])
        self.assertTrue(c["childhood_preservation"])
        self.assertTrue(c["expression_preservation"])
        self.assertLessEqual(c["max_strength"], sp.MAX_STRENGTH_CHILD)

    def test_profile_contains_no_geometry_or_identity_fields(self):
        """The identity guarantee lives here, in the data model.

        If a geometry key ever appears in the profile, downstream code can
        reshape a face, and no amount of prompting will stop it.
        """
        banned = (
            "face", "face_shape", "facemesh", "landmark", "landmarks", "eye",
            "eyes", "nose", "mouth", "lips", "jaw", "chin", "pose", "hair",
            "hairstyle", "body", "embedding", "identity", "arcface", "mesh",
            "warp", "thin", "slim", "enlarge", "geometry", "keypoint",
        )

        def walk(node, trail=""):
            if isinstance(node, dict):
                for key, value in node.items():
                    self.assertNotIn(
                        key.lower(), banned,
                        "identity-bearing key {!r} at {}".format(key, trail),
                    )
                    walk(value, trail + "." + str(key))
            elif isinstance(node, list):
                for i, value in enumerate(node):
                    walk(value, "{}[{}]".format(trail, i))

        walk(self.profile)

    def test_profile_survives_a_json_round_trip(self):
        text = json.dumps(self.profile, ensure_ascii=False)
        back = json.loads(text)
        self.assertEqual(back["color"]["mean_saturation"], self.profile["color"]["mean_saturation"])
        self.assertEqual(back["white_balance"]["temperature_hint"], self.profile["white_balance"]["temperature_hint"])

    def test_warm_reference_is_classified_warm(self):
        """Regression guard for an inverted-sign bug that shipped once.

        Gray-world gains NEUTRALISE the image (image = neutral / gain), so a
        warm photo has r_gain < b_gain. Reading the gains as if they were the
        look itself classifies every warm reference as cool.
        """
        wb = self.profile["white_balance"]
        self.assertEqual(wb["temperature_hint"], "warm")
        self.assertLess(wb["r_gain"], wb["b_gain"])

    def test_cool_target_is_classified_cool(self):
        wb = profile_of(self.tgt_rgb)["white_balance"]
        self.assertEqual(wb["temperature_hint"], "cool")
        self.assertGreater(wb["r_gain"], wb["b_gain"])

    def test_palette_is_deterministic(self):
        a = sp.extract_palette(sp.downscale(self.ref_rgb))
        b = sp.extract_palette(sp.downscale(self.ref_rgb))
        self.assertEqual(a, b)
        self.assertTrue(all("hex" in c and "weight" in c and "lab" in c for c in a))

    def test_skin_mask_is_selective_on_a_cool_frame(self):
        coverage = profile_of(self.tgt_rgb)["skin"]["coverage"]
        self.assertGreater(coverage, 0.002, "the subject should be detected as skin")
        self.assertLess(coverage, 0.6, "the cool background should not read as skin")

    def test_saturation_guard_disengages_when_the_mask_covers_the_frame(self):
        """Regression guard for a bug that silently froze the whole grade.

        Warm beige backgrounds are the same colour as skin, so the mask can
        match ~100% of the frame.  An earlier version damped the saturation
        change on every "skin" pixel, which then damped the entire image and
        the result never converged on the template.  The guard must disengage
        when the mask is too big to carry information.
        """
        flat = np.zeros((120, 160, 3), dtype=np.float32)
        flat[..., 0] = 0.08  # hue
        flat[..., 1] = 0.25  # saturation
        flat[..., 2] = 0.85  # value
        warm = np.clip(sp.hsv_to_rgb(flat), 0.0, 1.0).astype(np.float32)

        src = sp._single_profile(sp.downscale(warm))
        self.assertGreater(src["skin"]["coverage"], 0.6, "fixture should trip the guard")

        dst_sat = self.profile["color"]["mean_saturation"]
        out = apply_style.apply_style(warm, self.profile, 0.8, "color")
        after = sp._single_profile(sp.downscale(out))["color"]["mean_saturation"]

        # undamped the ratio is ~1.6x; the old damping landed at ~1.3x
        self.assertGreater(after, src["color"]["mean_saturation"] * 1.45)
        self.assertLess(after, dst_sat * 1.6, "the boost must not run past the template")

    def test_merging_several_references_reports_spread(self):
        merged = sp.compute_profile([self.reference, self.target], name="mixed")
        self.assertEqual(len(merged["source"]["references"]), 2)
        self.assertIn("dimension_variance", merged["source"])


# --------------------------------------------------------------------------
# compare / diagnose
# --------------------------------------------------------------------------


class CompareTests(StyleFixtures):
    def test_reference_compared_to_itself_needs_no_adjustment(self):
        dims = sp.compare_profile(self.reference, self.profile)
        self.assertEqual([d for d in dims if d["action"] == "adjust"], [])

    def test_cool_target_is_flagged_as_off_style(self):
        dims = sp.compare_profile(self.target, self.profile)
        off = [d["dimension"] for d in dims if d["action"] == "adjust"]
        self.assertTrue(off, "a cool dim target should differ from a warm reference")
        self.assertIn("white_balance.r_gain", off)

    def test_thresholds_are_per_dimension_not_one_global_number(self):
        """A single 0.25 threshold is meaningless across units.

        skin.warmth is Lab a* on a 0-30 scale; exposure.mean_luma is 0-1.
        """
        self.assertNotEqual(
            sp.threshold_for("skin.warmth"),
            sp.threshold_for("exposure.mean_luma"),
        )
        self.assertGreater(sp.threshold_for("skin.warmth"), 1.0)
        self.assertLess(sp.threshold_for("white_balance.r_gain"), 0.2)

    def test_compare_output_is_serialisable(self):
        dims = sp.compare_profile(self.target, self.profile)
        json.dumps(dims, ensure_ascii=False)
        for d in dims:
            self.assertIn("dimension", d)
            self.assertIn("action", d)
            self.assertIn(d["action"], ("adjust", "skip"))
            self.assertIn("threshold", d)


# --------------------------------------------------------------------------
# apply: the core business
# --------------------------------------------------------------------------


class ApplyStyleTests(StyleFixtures):
    def test_luma_moves_toward_the_profile(self):
        before = profile_of(self.tgt_rgb)["exposure"]["mean_luma"]
        want = self.profile["exposure"]["mean_luma"]
        after = profile_of(self.styled())["exposure"]["mean_luma"]
        self.assertGreater(want, before, "fixture: reference should be brighter")
        self.assertGreater(after, before)
        self.assertLess(abs(after - want), abs(before - want))

    def test_saturation_moves_toward_the_profile(self):
        before = profile_of(self.tgt_rgb)["color"]["mean_saturation"]
        want = self.profile["color"]["mean_saturation"]
        after = profile_of(self.styled())["color"]["mean_saturation"]
        self.assertGreater(want, before, "fixture: reference should be richer")
        self.assertGreater(after, before)
        self.assertLess(abs(after - want), abs(before - want))

    def test_temperature_moves_toward_the_profile(self):
        after = profile_of(self.styled())["white_balance"]["temperature_hint"]
        self.assertEqual(profile_of(self.tgt_rgb)["white_balance"]["temperature_hint"], "cool")
        self.assertEqual(after, self.profile["white_balance"]["temperature_hint"])

    def test_skin_saturation_does_not_overshoot_the_reference(self):
        want = self.profile["skin"]["saturation"]
        after = profile_of(self.styled())["skin"]["saturation"]
        self.assertLessEqual(after, want * 1.15 + 0.02)

    def test_highlight_clipping_stays_low(self):
        """Style transfer must not blow the highlights to make the numbers match."""
        out = self.styled()
        luma = sp.to_luma(out)
        clipped = float((luma > 0.985).mean())
        self.assertLess(clipped, 0.01, "clipped {:.4%} of pixels".format(clipped))

    def test_no_shadow_crush_either(self):
        out = self.styled()
        luma = sp.to_luma(out)
        self.assertLess(float((luma < 0.015).mean()), 0.01)

    def test_zero_strength_returns_the_original(self):
        np.testing.assert_allclose(self.styled(strength=0.0), self.tgt_rgb, atol=1e-6)

    def test_strength_is_clamped_to_the_child_limit(self):
        """Children get a hard ceiling on tonal shift that adults do not."""
        soft = self.styled(strength=0.5)
        hard = self.styled(strength=1.0)
        capped = self.styled(strength=sp.MAX_STRENGTH_CHILD)
        self.assertGreater(
            float(np.abs(hard - soft).mean()), 0.0, "strength should have an effect"
        )
        np.testing.assert_allclose(hard, capped, atol=1e-6)

    def test_a_stronger_strength_lands_closer_to_the_profile(self):
        want = self.profile["color"]["mean_saturation"]
        near = profile_of(self.styled(strength=0.3))["color"]["mean_saturation"]
        far = profile_of(self.styled(strength=sp.MAX_STRENGTH_CHILD))["color"]["mean_saturation"]
        self.assertLess(abs(far - want), abs(near - want))

    def test_composition_role_touches_no_pixels(self):
        out = apply_style.apply_style(self.tgt_rgb, self.profile, 0.8, "composition")
        np.testing.assert_allclose(out, self.tgt_rgb, atol=1e-6)

    def test_output_keeps_the_original_geometry(self):
        out = self.styled()
        self.assertEqual(out.shape, self.tgt_rgb.shape)

    def test_the_style_pass_is_pixelwise_not_a_repaint(self):
        """Equal input pixels must map to equal output pixels.

        This is the structural reason the style pass cannot alter identity.
        Any convolution (blur, sharpen, frequency separation), any
        content-aware fill, and any generative repaint gives two pixels with
        the same colour but different neighbourhoods different results.  A
        per-pixel colour mapping cannot -- so it is incapable of inventing or
        erasing a facial feature, no matter what the profile says.

        (A global grade does legitimately read the frame's histogram, so the
        whole image shares one curve.  That is grading, not regeneration --
        the curve is a function of the pixel's own value, plus scalars.)
        """
        profile = json.loads(json.dumps(self.profile))
        profile["background"]["vignette"] = 0.0  # vignette is positional by design

        h, w = 200, 260
        yy = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
        xx = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :]
        base = np.stack(
            [
                0.35 + 0.30 * np.sin(9.0 * xx + 3.0 * yy),
                0.40 + 0.25 * np.sin(7.0 * yy - 2.0 * xx),
                0.50 + 0.20 * np.cos(5.0 * xx + 6.0 * yy),
            ],
            axis=-1,
        ).astype(np.float32)
        # quantise so that thousands of pixels share an exact RGB triple
        img = np.round(np.clip(base, 0.0, 1.0) * 23.0) / 23.0

        out = apply_style.apply_style(img, profile, 0.8, "color")

        flat_in = img.reshape(-1, 3)
        flat_out = out.reshape(-1, 3)
        keys, inverse = np.unique(flat_in, axis=0, return_inverse=True)

        order = np.argsort(inverse, kind="stable")
        grouped = flat_out[order]
        bounds = np.flatnonzero(np.diff(inverse[order])) + 1
        starts = np.concatenate(([0], bounds, [len(order)]))
        lengths = np.diff(starts)

        seg_max = np.maximum.reduceat(grouped, starts[:-1])
        seg_min = np.minimum.reduceat(grouped, starts[:-1])
        spread = (seg_max - seg_min).max(axis=1)

        repeated = lengths > 1
        self.assertGreater(
            int(repeated.sum()), 100,
            "fixture should produce many tied pixels, got {}".format(int(repeated.sum())),
        )
        worst = float(spread[repeated].max())
        self.assertLess(
            worst, 1e-6,
            "two identical pixels came out different (spread {:.3g}) -- the "
            "pass is mixing neighbourhoods, which is not identity-safe".format(worst),
        )

    def test_unknown_role_is_rejected_loudly(self):
        with self.assertRaises(ValueError):
            apply_style.apply_style(self.tgt_rgb, self.profile, 0.8, "face_swap")

    def test_apply_is_deterministic(self):
        a = apply_style.apply_style(self.tgt_rgb, self.profile, 0.8, "target")
        b = apply_style.apply_style(self.tgt_rgb, self.profile, 0.8, "target")
        np.testing.assert_allclose(a, b, atol=1e-6)


# --------------------------------------------------------------------------
# iteration: the user says "再暖一点" and we go round again
# --------------------------------------------------------------------------


class IterationTests(StyleFixtures):
    def test_repeated_rounds_settle_instead_of_drifting(self):
        """Iteration is the whole point; a slow drift would ruin it.

        White balance removes a cool frame's cast, and that cast is most of
        its colour, so the saturation step has to climb a long way back.  An
        earlier ratio cap of 2.0 made the template unreachable and every
        round overshot a little further: 0.44 -> 0.48 -> 0.50.  The result
        must converge to a fixed point instead.
        """
        cur = self.tgt_rgb
        sats = []
        for _ in range(4):
            cur = apply_style.apply_style(cur, self.profile, 0.8, "color")
            sats.append(profile_of(cur)["color"]["mean_saturation"])

        self.assertGreater(sats[0], profile_of(self.tgt_rgb)["color"]["mean_saturation"])
        self.assertLess(
            abs(sats[-1] - sats[-2]), 0.02,
            "saturation is still moving after four rounds: {}".format(
                ["%.4f" % s for s in sats]),
        )
        self.assertLessEqual(
            sats[-1], self.profile["color"]["mean_saturation"] * 1.30,
            "saturation ran away from the template: {}".format(["%.4f" % s for s in sats]),
        )

    def test_clipping_never_appears_across_rounds(self):
        cur = self.tgt_rgb
        for _ in range(4):
            cur = apply_style.apply_style(cur, self.profile, 0.8, "color")
            self.assertLess(float((sp.to_luma(cur) > 0.985).mean()), 0.01)

    def test_gates_report_no_work_for_a_frame_that_already_matches(self):
        """Minimum edit principle: do not re-grade what is already right."""
        for step in ("white_balance", "tone", "saturation"):
            self.assertFalse(
                apply_style._needs(self.ref_rgb, self.profile, step),
                "{} claims work on the very image the profile came from".format(step),
            )

    def test_gates_report_work_for_a_frame_that_does_not_match(self):
        for step in ("white_balance", "tone", "saturation"):
            self.assertTrue(
                apply_style._needs(self.tgt_rgb, self.profile, step),
                "{} missed an obviously off-style frame".format(step),
            )

    def test_each_gate_is_judged_on_the_state_it_would_change(self):
        """The steps are coupled: a tone curve lifts saturation too.

        Deciding every gate up front, against the input image, lets saturation
        drift away round after round while the saturation step sits idle
        because it looked fine before the tone ran.
        """
        warmed = apply_style.apply_white_balance(
            self.tgt_rgb, apply_style._live_stats(self.tgt_rgb), self.profile, 0.8
        )
        # warming neutralised the cast, so saturation collapsed -- the gate
        # has to see that, not the input frame's number
        self.assertLess(
            apply_style._live_stats(warmed)["color"]["mean_saturation"],
            apply_style._live_stats(self.tgt_rgb)["color"]["mean_saturation"],
        )
        self.assertTrue(apply_style._needs(warmed, self.profile, "saturation"))

    def test_saturation_reaches_the_template_at_full_strength(self):
        cur = apply_style.apply_style(self.tgt_rgb, self.profile, sp.MAX_STRENGTH_CHILD, "color")
        got = profile_of(cur)["color"]["mean_saturation"]
        want = self.profile["color"]["mean_saturation"]
        self.assertLess(abs(got - want), 0.06, "got {:.4f}, wanted {:.4f}".format(got, want))


class CompareReliabilityTests(StyleFixtures):
    def test_skin_dimensions_are_ignored_when_a_mask_is_not_selective(self):
        """A confident number measured on the wrong pixels is worse than none.

        Here the profile's own skin mask covers 86% of the reference frame, so
        its `skin.warmth` is the average colour of the whole picture.  Acting
        on the delta would warm skin that just got warmer.
        """
        rows = {d["dimension"]: d for d in sp.compare_profile(self.target, self.profile)}
        self.assertGreater(self.profile["skin"]["coverage"], 0.6)
        self.assertEqual(rows["skin.warmth"]["action"], "skip")
        self.assertIn("unreliable", rows["skin.warmth"]["note"])

    def test_skin_dimensions_are_judged_normally_when_both_masks_are_selective(self):
        profile = json.loads(json.dumps(self.profile))
        profile["skin"]["coverage"] = 0.30
        profile["skin"]["warmth"] = 20.0  # far from the target's 8.18

        rows = {d["dimension"]: d for d in sp.compare_profile(self.target, profile)}
        self.assertEqual(rows["skin.warmth"]["action"], "adjust")
        self.assertIsNone(rows["skin.warmth"]["note"])


# --------------------------------------------------------------------------
# the tone curve: why clipping is structurally impossible
# --------------------------------------------------------------------------


def _lut(source_mean=0.35, target_mean=0.75, strength=0.85, contrast=0.18,
         shadow=0.25, high=0.85):
    rng = np.random.default_rng(0)
    source_luma = np.clip(
        rng.normal(source_mean, 0.15, 20000), 0.0, 1.0
    ).astype(np.float32)
    return apply_style.build_tone_lut(
        source_luma,
        target_mean=target_mean,
        target_contrast=contrast,
        target_shadow=shadow,
        target_high=high,
        strength=strength,
    )


class ToneCurveTests(unittest.TestCase):
    def test_lut_is_monotone(self):
        x, lut = _lut()
        self.assertTrue(np.all(np.diff(lut) >= -1e-9), "a non-monotone curve inverts tones")

    def test_lut_endpoints_are_pinned(self):
        x, lut = _lut()
        self.assertAlmostEqual(float(lut[0]), 0.0, places=6)
        self.assertAlmostEqual(float(lut[-1]), 1.0, places=6)
        self.assertTrue(np.all(lut >= 0.0) and np.all(lut <= 1.0))

    def test_lut_stays_legal_under_aggressive_targets(self):
        for target_mean in (0.05, 0.5, 0.95):
            for strength in (0.2, 0.85):
                x, lut = _lut(target_mean=target_mean, strength=strength)
                self.assertTrue(np.all(np.diff(lut) >= -1e-9))
                self.assertTrue(np.all(lut >= 0.0) and np.all(lut <= 1.0))

    def test_zero_strength_is_the_identity_curve(self):
        x, lut = _lut(strength=0.0)
        np.testing.assert_allclose(lut, x, atol=1e-6)

    def test_exposure_curve_compresses_highlights_instead_of_clipping(self):
        """The shoulder: it must roll off, never clip.

        Note this curve is deliberately compressive at the top even at gain 1
        -- that roll-off is what keeps skin and white clothing from turning
        into featureless blobs.  `build_tone_lut` skips the exposure step
        entirely when the frame is already within 0.02 of the target mean, so
        a correctly exposed photo is never pushed through it.
        """
        ramp = np.linspace(0.0, 1.0, 11, dtype=np.float64)
        out = apply_style.exposure_curve(ramp, 2.0)

        self.assertAlmostEqual(float(out[0]), 0.0, places=6)
        self.assertLessEqual(float(out.max()), 1.0, "the shoulder must not reach white")
        self.assertTrue(np.all(np.diff(out) > 0.0), "exposure must stay monotone")

        steps = np.diff(out)
        self.assertTrue(np.all(np.diff(steps) <= 1e-9), "the curve must be concave")
        self.assertLess(
            steps[-1], steps[0],
            "highlight steps must be smaller than shadow steps -- that is the shoulder",
        )

    def test_exposure_gain_solver_hits_the_target_mean(self):
        rng = np.random.default_rng(1)
        luma = np.clip(rng.normal(0.4, 0.15, 8000), 0.0, 1.0).astype(np.float32)
        gain = apply_style._solve_exposure_gain(luma, 0.62)
        self.assertGreater(gain, 0.0)
        self.assertAlmostEqual(
            float(apply_style.exposure_curve(luma, gain).mean()), 0.62, delta=0.01
        )

    def test_soft_clip_never_exceeds_one(self):
        x = np.array([0.0, 0.5, 0.86, 0.95, 1.0, 1.4])
        out = apply_style.soft_clip_highlights(x)
        self.assertTrue(np.all(out <= 1.0 + 1e-9))
        self.assertAlmostEqual(float(out[0]), 0.0, places=6)
        self.assertLess(float(out[-1]), 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
