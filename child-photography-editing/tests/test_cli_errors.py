import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


class CliErrorTest(unittest.TestCase):
    def _run(self, script: str, *arguments: str):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / script), *arguments],
            capture_output=True,
            encoding="utf-8",
            check=False,
        )

    def test_json_clis_report_malformed_input_without_tracebacks(self):
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / "bad.json"
            bad.write_text("{not-json", encoding="utf-8")
            valid = Path(directory) / "valid.json"
            valid.write_text("{}", encoding="utf-8")
            cases = (
                ("validate_edit_plan.py", str(bad)),
                ("build_generation_prompt.py", str(bad), str(valid)),
                ("style_profile.py", "--observations", "{not-json"),
                ("batch_manifest.py", "--batch-lock", "{not-json"),
            )
            for case in cases:
                with self.subTest(script=case[0]):
                    result = self._run(*case)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("invalid JSON", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    def test_image_cli_reports_missing_file_without_traceback(self):
        result = self._run("analyze_image.py", "definitely-missing-image.jpg")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot read image", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
