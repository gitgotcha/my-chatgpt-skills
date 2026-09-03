import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyze_image import analyze_image
from fixtures import synthetic_jpeg, synthetic_png


class AnalyzeImageTest(unittest.TestCase):
    def _analyze_bytes(self, data: bytes, suffix: str):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / f"synthetic{suffix}"
            path.write_bytes(data)
            before = path.read_bytes()
            result = analyze_image(path)
            after = path.read_bytes()
        return result, before, after

    def test_synthetic_png_dimensions_and_orientation(self):
        result, _, _ = self._analyze_bytes(synthetic_png(1200, 2000), ".png")
        self.assertEqual((result["width"], result["height"]), (1200, 2000))
        self.assertEqual(result["orientation"], "portrait-or-square")

    def test_synthetic_jpeg_sof_dimensions_and_orientation(self):
        result, _, _ = self._analyze_bytes(synthetic_jpeg(2000, 1200), ".jpg")
        self.assertEqual((result["width"], result["height"]), (2000, 1200))
        self.assertEqual(result["orientation"], "landscape")

    def test_unknown_format_has_unknown_orientation(self):
        result, _, _ = self._analyze_bytes(b"not an image", ".dat")
        self.assertIsNone(result["width"])
        self.assertIsNone(result["height"])
        self.assertEqual(result["orientation"], "unknown")

    def test_truncated_png_is_reported_as_unknown_instead_of_crashing(self):
        try:
            result, _, _ = self._analyze_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", ".png")
        except Exception as exc:
            self.fail(f"truncated PNG raised {type(exc).__name__}: {exc}")
        self.assertEqual(result["orientation"], "unknown")

    def test_analysis_hashes_without_modifying_source(self):
        data = synthetic_jpeg(640, 480)
        result, before, after = self._analyze_bytes(data, ".jpg")
        self.assertEqual(before, data)
        self.assertEqual(after, data)
        self.assertEqual(result["sha256"], hashlib.sha256(data).hexdigest())


if __name__ == "__main__":
    unittest.main()
