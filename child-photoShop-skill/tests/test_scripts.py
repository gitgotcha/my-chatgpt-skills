"""Tests for the deterministic helper scripts.

None of these are a retouching engine -- they only do what an agent is bad at
(arithmetic, hashing, bookkeeping) so that the agent's judgement calls are
made against real numbers instead of vibes.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import analyze_image  # noqa: E402
import batch_manifest as bm  # noqa: E402
import contact_sheet as cs  # noqa: E402
import duplicate_detection as dd  # noqa: E402
import fixtures  # noqa: E402
import image_quality as iq  # noqa: E402


class ScriptFixtureCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = cls._tmp.name
        cls.built = fixtures.build_all(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()


# --------------------------------------------------------------------------
# image quality: the scores have to separate good frames from bad ones
# --------------------------------------------------------------------------


class ImageQualityTests(ScriptFixtureCase):
    def test_sharp_frames_score_far_above_the_blurry_one(self):
        """A score that puts a sharp photo at 0.02 is unusable.

        An earlier version normalised Laplacian variance by a constant, which
        buried every real photo near zero.  These are saturating maps, so a
        good frame lands high and a soft frame lands low.
        """
        sharp = [iq.score_image(p) for p in self.built["burst"][:3]]
        blurry = iq.score_image(self.built["blur"])

        for s in sharp:
            self.assertGreater(s["sharpness"], 0.25, "sharp frame scored low")
        self.assertLess(blurry["sharpness"], 0.10, "blurry frame scored high")
        self.assertGreater(
            min(s["sharpness"] for s in sharp) - blurry["sharpness"], 0.2,
            "the two classes are not separated enough to rank by",
        )

    def test_detail_tracks_sharpness_instead_of_inverting_it(self):
        """A field named `blur` that rose on sharp frames shipped once.

        The agent reads these numbers to decide what to keep, so a metric
        whose name inverts its meaning is worse than having no metric.
        """
        blurry = iq.score_image(self.built["blur"])
        sharp = iq.score_image(self.built["burst"][0])
        self.assertGreater(sharp["detail"], blurry["detail"])
        self.assertNotIn("blur", sharp, "the misleading `blur` key is back")

    def test_scores_are_bounded(self):
        for path in self.built["burst"] + [self.built["blur"]]:
            s = iq.score_image(path)
            for key in ("sharpness", "detail", "exposure", "brightness"):
                self.assertGreaterEqual(s[key], 0.0, key)
                self.assertLessEqual(s[key], 1.0, key)

    def test_exposure_is_reported_for_a_well_lit_reference(self):
        ref = fixtures.build_warm_reference(os.path.join(self.tmp, "q_ref.jpg"))
        s = iq.score_image(ref)
        self.assertGreater(s["brightness"], 0.4)
        self.assertGreater(s["exposure"], 0.5)

    def test_score_array_agrees_with_score_image(self):
        path = self.built["burst"][0]
        from PIL import Image

        rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
        a = iq.score_array(rgb)
        b = iq.score_image(path)
        self.assertAlmostEqual(a["sharpness"], b["sharpness"], delta=0.05)

    def test_missing_file_is_reported_not_raised(self):
        s = iq.score_image(os.path.join(self.tmp, "nope.jpg"))
        self.assertIn("error", s)


# --------------------------------------------------------------------------
# burst dedup
# --------------------------------------------------------------------------


class DuplicateDetectionTests(ScriptFixtureCase):
    def test_a_burst_collapses_into_one_group(self):
        """The fixture is `count` near-identical frames plus one that changed.

        Only the near-identical ones belong in the cluster -- the last frame
        moved the subject and must survive as its own photograph.
        """
        burst = sorted(self.built["burst"])
        groups = dd.find_duplicate_groups(burst, window=12, threshold=10)
        self.assertEqual(len(groups), 1, "one burst should form one cluster")
        self.assertEqual(len(groups[0]["images"]), len(burst) - 1)
        self.assertNotIn(
            os.path.basename(burst[-1]), groups[0]["images"],
            "the frame that changed composition got merged into the burst",
        )

    def test_unrelated_frames_stay_out_of_the_group(self):
        paths = sorted(self.built["burst"]) + [self.built["target"]]
        groups = dd.find_duplicate_groups(paths, window=12, threshold=10)
        covered = {n for g in groups for n in g["images"]}
        self.assertNotIn(
            os.path.basename(self.built["target"]), covered,
            "a completely different frame was pulled into the burst cluster",
        )

    def test_group_output_is_complete_and_serialisable(self):
        groups = dd.find_duplicate_groups(sorted(self.built["burst"]))
        json.dumps(groups)
        for g in groups:
            self.assertIn("group_id", g)
            self.assertIn("images", g)
            self.assertIn("paths", g)
            self.assertIn("max_distance", g)
            self.assertGreaterEqual(g["max_distance"], 0)

    def test_identical_files_have_zero_distance(self):
        p = self.built["burst"][0]
        self.assertEqual(dd.distance((dd.phash(p), dd.dhash(p)), (dd.phash(p), dd.dhash(p))), 0)

    def test_hashes_are_stable_across_calls(self):
        p = self.built["burst"][0]
        self.assertEqual(dd.phash(p), dd.phash(p))
        self.assertEqual(dd.dhash(p), dd.dhash(p))

    def test_empty_input_returns_no_groups(self):
        self.assertEqual(dd.find_duplicate_groups([]), [])

    def test_a_tight_window_prevents_distant_merges(self):
        """Time adjacency matters: the same pose hours apart is two moments."""
        paths = sorted(self.built["burst"])
        wide = dd.find_duplicate_groups(paths, window=12, threshold=10)
        tight = dd.find_duplicate_groups(paths, window=1, threshold=10)
        self.assertGreaterEqual(
            sum(len(g["images"]) for g in wide),
            sum(len(g["images"]) for g in tight),
        )


# --------------------------------------------------------------------------
# batch manifest: the audit trail
# --------------------------------------------------------------------------


class BatchManifestTests(ScriptFixtureCase):
    def setUp(self):
        self.folder = os.path.join(self.tmp, "session")
        os.makedirs(self.folder, exist_ok=True)
        for p in self.built["burst"][:4]:
            with open(p, "rb") as src:
                blob = src.read()
            with open(os.path.join(self.folder, os.path.basename(p)), "wb") as dst:
                dst.write(blob)
        self.path = os.path.join(self.tmp, "manifest.json")

    def test_init_records_every_image_as_pending(self):
        data = bm.create_manifest(self.folder, session="camping")
        self.assertEqual(data["session"], "camping")
        self.assertEqual(len(data["images"]), 4)
        self.assertTrue(all(i["status"] == "pending" for i in data["images"]))
        self.assertTrue(data["constraints"]["originals_preserved"])
        self.assertTrue(data["constraints"]["identity_lock"])

    def test_round_trip_through_disk(self):
        data = bm.create_manifest(self.folder)
        bm.save_manifest(self.path, data)
        back = bm.load_manifest(self.path)
        self.assertEqual(len(back["images"]), len(data["images"]))
        self.assertEqual(back["session"], data["session"])

    def test_qa_result_drives_the_status(self):
        data = bm.create_manifest(self.folder)
        name = data["images"][0]["filename"]
        bm.update_image(data, name, qa="pass", output="edited/a.jpg", backend="apply_style.py")
        bm.update_image(data, data["images"][1]["filename"], qa="fail", note="skin plastic")
        counts = bm.summary(data)
        self.assertEqual(counts.get("qa_passed"), 1)
        self.assertEqual(counts.get("qa_failed"), 1)
        self.assertEqual(data["images"][0]["output"], "edited/a.jpg")
        self.assertEqual(len(data["images"][1]["notes"]), 1)

    def test_updating_an_unknown_image_is_reported(self):
        data = bm.create_manifest(self.folder)
        self.assertFalse(bm.update_image(data, "ghost.jpg", status="edited"))

    def test_notes_accumulate_instead_of_overwriting(self):
        """Every iteration round must stay visible -- that is the audit trail."""
        data = bm.create_manifest(self.folder)
        name = data["images"][0]["filename"]
        bm.update_image(data, name, note="再暖一点")
        bm.update_image(data, name, note="再亮一点")
        self.assertEqual(len(data["images"][0]["notes"]), 2)


# --------------------------------------------------------------------------
# contact sheet and analysis
# --------------------------------------------------------------------------


class ContactSheetTests(ScriptFixtureCase):
    def test_builds_a_readable_grid(self):
        out = os.path.join(self.tmp, "sheet.jpg")
        cs.build_contact_sheet(sorted(self.built["burst"]), out, cols=3, thumb=180)
        self.assertTrue(os.path.exists(out))
        from PIL import Image

        with Image.open(out) as im:
            self.assertGreater(im.size[0], 400)
            self.assertGreater(im.size[1], 200)

    def test_missing_scores_do_not_break_the_sheet(self):
        out = os.path.join(self.tmp, "sheet2.jpg")
        cs.build_contact_sheet(sorted(self.built["burst"]), out, cols=2, thumb=120)
        self.assertTrue(os.path.exists(out))


class AnalyzeImageTests(ScriptFixtureCase):
    def test_reports_dimensions_and_histogram(self):
        info = analyze_image.analyze(self.built["burst"][0])
        self.assertGreater(info["width"], 0)
        self.assertGreater(info["height"], 0)
        self.assertEqual(info["filename"], os.path.basename(self.built["burst"][0]))
        hist = info["luminance"]["histogram"]
        self.assertEqual(len(hist), analyze_image.HIST_BINS)
        self.assertAlmostEqual(sum(hist), 1.0, delta=0.02)

    def test_output_is_serialisable(self):
        json.dumps(analyze_image.analyze(self.built["burst"][0]), ensure_ascii=False)

    def test_missing_file_is_reported_not_raised(self):
        info = analyze_image.analyze(os.path.join(self.tmp, "nope.jpg"))
        self.assertIn("error", info)


if __name__ == "__main__":
    unittest.main(verbosity=2)
