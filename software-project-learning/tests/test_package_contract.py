"""Package integrity only; teaching quality is evaluated with fresh agents.

Run: python -m unittest discover -s software-project-learning/tests -v
"""

import pathlib
import re
import unittest
from urllib.parse import unquote, urlsplit


SKILL_ROOT = pathlib.Path(__file__).resolve().parents[1]


class PackageContractTest(unittest.TestCase):
    def test_published_resources_decode_as_utf8(self):
        # Broken encoding prevents the host from displaying the skill metadata.
        resources = sorted(
            path for path in SKILL_ROOT.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix.lower() in {".md", ".yaml", ".yml", ".py"}
        )
        self.assertGreaterEqual(len(resources), 8, "skill package scan covered too few resources")
        for resource in resources:
            relative = resource.relative_to(SKILL_ROOT).as_posix()
            with self.subTest(resource=relative):
                text = resource.read_text(encoding="utf-8")
                self.assertTrue(text.strip(), "published resource is empty")
                self.assertNotIn("\ufffd", text, "lossy decoding was saved to disk")

    def test_relative_document_links_resolve(self):
        # A moved/deleted reference must not leave an unreadable skill route.
        for relative in ("SKILL.md", "README.md", "references/copy-paste-prompt.md"):
            document = SKILL_ROOT / relative
            text = document.read_text(encoding="utf-8")
            for target in re.findall(r"\[[^\]\n]+\]\(([^)\n]+)\)", text):
                parts = urlsplit(target.strip("<>"))
                if parts.scheme or not parts.path:
                    continue
                with self.subTest(document=relative, link=target):
                    self.assertTrue(
                        (document.parent / unquote(parts.path)).is_file(),
                        "linked resource is missing",
                    )


if __name__ == "__main__":
    unittest.main()
