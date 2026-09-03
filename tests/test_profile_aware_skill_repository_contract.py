"""Repository-level contract tests for the profile-aware skill creator.

These tests pin the repository router and persistence documentation in
``AGENTS.md`` and verify that no protected directory drifts from
``origin/main``.

Run from the repository root::

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_MD = REPO_ROOT / "AGENTS.md"

PROTECTED_PATHS = [
    "algorithm-learning",
    "backend-project-learning",
    "conducting-java-backend-mock-interviews",
    "java-knowledge-based-on-resume-learn-skill",
    "reviewing-java-backend-interviews",
    "cloud-mcp",
]

NEW_LOGICAL_OPERATIONS = [
    "system.capabilities.read",
    "system.user.resolve",
    "profile.snapshot.read",
    "profile.evidence.recorded",
]


def _read_agents_md() -> str:
    return AGENTS_MD.read_text(encoding="utf-8")


class RouterContractTest(unittest.TestCase):
    """The router must route to the meta Skill and mark it explicit."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = _read_agents_md()

    def test_router_lists_profile_aware_skill_creator(self) -> None:
        self.assertIn("profile-aware-skill-creator/SKILL.md", self.text)

    def test_router_entry_is_marked_explicit(self) -> None:
        entry_lines = [
            line for line in self.text.splitlines()
            if "profile-aware-skill-creator/SKILL.md" in line
        ]
        self.assertTrue(entry_lines, "router entry missing")
        for line in entry_lines:
            lowered = line.lower()
            self.assertTrue(
                "explicit" in lowered or "显式" in line,
                "router entry must mark the meta Skill as explicit-only",
            )


class PersistenceContractTest(unittest.TestCase):
    """The persistence documentation must recognize the generic profile path."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = _read_agents_md()

    def test_profile_namespace_is_documented(self) -> None:
        self.assertIn("profile", self.text)

    def test_four_new_logical_operations_are_documented(self) -> None:
        for operation in NEW_LOGICAL_OPERATIONS:
            self.assertIn(operation, self.text, f"missing operation {operation}")

    def test_generic_receipts_are_asynchronous_without_drive_fileid(self) -> None:
        flattened = " ".join(self.text.split())
        self.assertIn("pending", flattened)
        self.assertIn("cloud_accepted", flattened)
        self.assertIn("fileId", flattened)
        self.assertIn("no immediate Drive", flattened)

    def test_existing_skills_are_not_migrated(self) -> None:
        flattened = " ".join(self.text.split()).lower()
        self.assertTrue(
            any(phrase in flattened for phrase in
                ["not migrate", "not migrated", "does not migrate"]),
            "Phase 1 non-migration of existing skills must be documented",
        )

    def test_capability_negotiation_is_documented(self) -> None:
        self.assertIn("system.capabilities.read", self.text)
        self.assertIn("reliable-drive-sync", self.text)


class LegacyContractPreservedTest(unittest.TestCase):
    """Old events, domains, output paths and migration rules stay documented."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = _read_agents_md()

    def test_old_namespaces_are_still_listed(self) -> None:
        for namespace in ["algorithm", "interview", "resume-knowledge", "system"]:
            self.assertIn(namespace, self.text)

    def test_old_event_types_are_still_listed(self) -> None:
        for event_type in [
            "system.user-registered",
            "algorithm.learning.completed",
        ]:
            self.assertIn(event_type, self.text)

    def test_identity_rules_are_preserved(self) -> None:
        self.assertIn("NFKC", self.text)
        self.assertIn("userId", self.text)

    def test_local_output_paths_are_preserved(self) -> None:
        self.assertIn("outputs/interview/", self.text)

    def test_migration_rules_are_preserved(self) -> None:
        self.assertIn("system.legacy-migration-requested", self.text)
        self.assertIn("dry-run", self.text)


class CloudMcpBoundaryTest(unittest.TestCase):
    """cloud-mcp must be named as frozen compatibility code, not the runtime."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = _read_agents_md()

    def test_cloud_mcp_is_frozen_compatibility_code(self) -> None:
        lowered = self.text.lower()
        self.assertIn("cloud-mcp", lowered)
        self.assertTrue(
            any(word in lowered for word in ["frozen", "legacy", "compatib"]),
            "cloud-mcp must be described as frozen/legacy compatibility code",
        )
        self.assertIn("profile", self.text)


class ProtectedPathsTest(unittest.TestCase):
    """Protected directories must have zero diff versus origin/main."""

    def test_protected_paths_are_unchanged(self) -> None:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(REPO_ROOT),
                "diff",
                "origin/main",
                "--",
                *PROTECTED_PATHS,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(),
            "",
            "protected paths must not differ from origin/main",
        )


if __name__ == "__main__":
    unittest.main()
