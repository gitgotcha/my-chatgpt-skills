"""Repository contract for the unified software project learning skill."""

from __future__ import annotations

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "software-project-learning"


class UnifiedSkillContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.router = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")

    def test_package_has_one_canonical_name(self) -> None:
        self.assertRegex(self.skill, r"(?m)^name: software-project-learning$")
        self.assertIn("software-project-learning/SKILL.md", self.router)
        active_router = self.router.split("## Persistence contract", 1)[0]
        self.assertNotIn("backend-project-learning/SKILL.md", active_router)
        self.assertNotIn("development-plan-learning/SKILL.md", active_router)

    def test_two_mode_resources_are_published(self) -> None:
        for relative in (
            "references/standard-mode.md",
            "references/interview-mode.md",
            "references/project-modeling.md",
            "references/source-tracing.md",
            "references/reliability-review.md",
            "tests/behavior-scenarios.md",
        ):
            with self.subTest(relative=relative):
                resource = SKILL_ROOT / relative
                self.assertTrue(resource.is_file(), relative)
                self.assertTrue(resource.read_text(encoding="utf-8").strip(), relative)

    def test_retired_duplicate_packages_are_absent(self) -> None:
        self.assertFalse((REPO_ROOT / "backend-project-learning").exists())
        self.assertFalse((REPO_ROOT / "development-plan-learning").exists())


if __name__ == "__main__":
    unittest.main()
