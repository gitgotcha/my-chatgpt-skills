"""Behavior tests for scripts/validate_profile_skill.py.

The tests build disposable Skill trees inside ``tempfile.TemporaryDirectory``
and invoke the validator's public function and CLI. Only the standard library
is used.

Run from ``profile-aware-skill-creator``::

    python -m unittest tests.test_validate_profile_skill -v
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = SKILL_ROOT / "scripts" / "validate_profile_skill.py"

RUNTIME_TOOL = "submit_event"
RUNTIME_OPERATIONS = {
    "tool": RUNTIME_TOOL,
    "capabilitiesEvent": "system.capabilities.read",
    "identityResolveEvent": "system.user.resolve",
    "identityRegisterEvent": "system.user-registered",
    "profileReadEvent": "profile.snapshot.read",
    "evidenceWriteEvent": "profile.evidence.recorded",
    "directDriveAccess": False,
}
PLATFORMS = ["codex", "chatgpt", "claude", "workbuddy"]
ALLOWED_OUTCOMES = [
    "observed", "consulted", "stuck", "incorrect", "partial",
    "completed", "correct", "passed", "failed",
]

PLAIN_SKILL_MD = """---
name: release-notes
description: Use when the user asks to draft accurate release notes from verified changes.
---

# Release Notes

Draft release notes from verified, user-relevant changes.
"""

PROFILE_SKILL_MD = """---
name: english-learning
description: Use when the user asks for personalized English coaching backed by a persistent learner profile.
---

# English Learning

Coach the learner and record observable evidence per the profile contract.

Read [references/profile-contract.md](references/profile-contract.md) before
reading or recording profile evidence.
"""

PROFILE_CONTRACT_MD = """# Profile Contract

## Capability Gate

Call system.capabilities.read before any profile operation.

## Identity and Consent

Resolve the user and require explicit consent before registration.

## Snapshot Read

Read the profile with profile.snapshot.read before personalization.

## Evidence Recording

Record at most one consolidated profile.evidence.recorded event per task.

## Correction Events

Corrections use supersede or invalidate with a targetEventKey from evidenceRefs.

## Failure and Receipt Wording

pending means locally retained; cloud_accepted means accepted with background sync.
"""

PROFILE_TEST_PY = """import unittest


class ProfileContractTest(unittest.TestCase):
    def test_placeholder_real_assertions_run_here(self) -> None:
        self.assertTrue(True)
"""


def _capability_document(domain: str = "english-learning", source_skill: str = "english-learning") -> dict:
    return {
        "schemaVersion": "1.0",
        "domain": domain,
        "sourceSkill": source_skill,
        "dimensions": [
            {
                "dimensionKey": "vocabulary",
                "subjectKeyDescription": "observed word or phrase key",
                "description": "vocabulary understanding and active use",
            }
        ],
        "evidencePolicy": {
            "recordWhen": ["the user gives a checkable answer or attempt"],
            "doNotRecordWhen": ["only model speculation without observable behavior"],
            "allowedOutcomes": ALLOWED_OUTCOMES,
            "sourceRefPolicy": "each independent evidence uses a stable distinct source reference",
            "minimumEvidenceTextLength": 8,
        },
        "runtime": dict(RUNTIME_OPERATIONS),
        "portability": {
            "platforms": list(PLATFORMS),
            "coreContractDependsOnOpenaiYaml": False,
        },
    }


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_profile_skill", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_plain_skill(root: Path) -> Path:
    skill_dir = root / "release-notes"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(PLAIN_SKILL_MD, encoding="utf-8")
    return skill_dir


def _write_profile_skill(root: Path) -> Path:
    skill_dir = root / "english-learning"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(PROFILE_SKILL_MD, encoding="utf-8")
    references = skill_dir / "references"
    references.mkdir()
    (references / "profile-contract.md").write_text(PROFILE_CONTRACT_MD, encoding="utf-8")
    schemas = skill_dir / "schemas"
    schemas.mkdir()
    (schemas / "profile-capability.json").write_text(
        json.dumps(_capability_document(), indent=2), encoding="utf-8"
    )
    tests = skill_dir / "tests"
    tests.mkdir()
    (tests / "test_profile_contract.py").write_text(PROFILE_TEST_PY, encoding="utf-8")
    return skill_dir


class ValidatorBehaviorTest(unittest.TestCase):
    """Behavioral contract of validate_skill() and the CLI."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = _load_validator()

    def test_valid_plain_skill_passes_plain_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_plain_skill(Path(tmp))
            errors = self.validator.validate_skill(skill_dir, "plain")
            self.assertEqual(errors, [])

    def test_plain_mode_rejects_profile_only_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_profile_skill(Path(tmp))
            errors = self.validator.validate_skill(skill_dir, "plain")
            self.assertTrue(errors)
            self.assertTrue(any("profile-contract.md" in e for e in errors))

    def test_plain_mode_rejects_profile_event_types(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_plain_skill(Path(tmp))
            (skill_dir / "SKILL.md").write_text(
                PLAIN_SKILL_MD + "\nCall profile.snapshot.read.\n", encoding="utf-8"
            )
            errors = self.validator.validate_skill(skill_dir, "plain")
            self.assertTrue(any("profile" in e for e in errors))

    def test_valid_profile_skill_passes_profile_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_profile_skill(Path(tmp))
            errors = self.validator.validate_skill(skill_dir, "profile")
            self.assertEqual(errors, [])

    def test_profile_mode_rejects_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_profile_skill(Path(tmp))
            (skill_dir / "schemas" / "profile-capability.json").unlink()
            errors = self.validator.validate_skill(skill_dir, "profile")
            self.assertTrue(any("profile-capability.json" in e for e in errors))

    def test_profile_mode_rejects_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_profile_skill(Path(tmp))
            (skill_dir / "schemas" / "profile-capability.json").write_text(
                "{not json", encoding="utf-8"
            )
            errors = self.validator.validate_skill(skill_dir, "profile")
            self.assertTrue(any("profile-capability.json" in e for e in errors))

    def test_profile_mode_rejects_reserved_domain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_profile_skill(Path(tmp))
            (skill_dir / "schemas" / "profile-capability.json").write_text(
                json.dumps(_capability_document(domain="algorithm")), encoding="utf-8"
            )
            errors = self.validator.validate_skill(skill_dir, "profile")
            self.assertTrue(any("domain" in e for e in errors))

    def test_profile_mode_rejects_source_skill_name_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_profile_skill(Path(tmp))
            (skill_dir / "schemas" / "profile-capability.json").write_text(
                json.dumps(_capability_document(source_skill="other-skill")),
                encoding="utf-8",
            )
            errors = self.validator.validate_skill(skill_dir, "profile")
            self.assertTrue(any("sourceSkill" in e for e in errors))

    def test_profile_mode_rejects_empty_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_profile_skill(Path(tmp))
            document = _capability_document()
            document["dimensions"] = []
            (skill_dir / "schemas" / "profile-capability.json").write_text(
                json.dumps(document), encoding="utf-8"
            )
            errors = self.validator.validate_skill(skill_dir, "profile")
            self.assertTrue(any("dimensions" in e for e in errors))

    def test_profile_mode_rejects_altered_runtime_constants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_profile_skill(Path(tmp))
            document = _capability_document()
            document["runtime"] = {
                **RUNTIME_OPERATIONS,
                "profileReadEvent": "profile.snapshot.fetch",
            }
            (skill_dir / "schemas" / "profile-capability.json").write_text(
                json.dumps(document), encoding="utf-8"
            )
            errors = self.validator.validate_skill(skill_dir, "profile")
            self.assertTrue(any("runtime" in e for e in errors))

    def test_profile_mode_rejects_unknown_top_level_capability_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_profile_skill(Path(tmp))
            document = _capability_document()
            document["unknownTopField"] = "should not be here"
            (skill_dir / "schemas" / "profile-capability.json").write_text(
                json.dumps(document), encoding="utf-8"
            )
            errors = self.validator.validate_skill(skill_dir, "profile")
            self.assertTrue(
                any("unknown" in e for e in errors) or any("field" in e and "should not" not in e for e in errors)
            )

    def test_profile_mode_rejects_unknown_runtime_capability_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_profile_skill(Path(tmp))
            document = _capability_document()
            document["runtime"]["unknownRuntimeField"] = "invalid"
            (skill_dir / "schemas" / "profile-capability.json").write_text(
                json.dumps(document), encoding="utf-8"
            )
            errors = self.validator.validate_skill(skill_dir, "profile")
            self.assertTrue(
                any("unknown" in e for e in errors) or any("runtime" in e and "field" in e for e in errors)
            )

    def test_profile_mode_rejects_direct_drive_access_constant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_profile_skill(Path(tmp))
            document = _capability_document()
            document["runtime"] = {**RUNTIME_OPERATIONS, "directDriveAccess": True}
            (skill_dir / "schemas" / "profile-capability.json").write_text(
                json.dumps(document), encoding="utf-8"
            )
            errors = self.validator.validate_skill(skill_dir, "profile")
            self.assertTrue(any("directDriveAccess" in e for e in errors))

    def test_hardcoded_home_paths_are_rejected(self) -> None:
        for bad_path in ["C:\\Users\\alice\\notes", "/Users/alice/notes", "/home/alice/notes", "/root/notes"]:
            with self.subTest(path=bad_path):
                with tempfile.TemporaryDirectory() as tmp:
                    skill_dir = _write_plain_skill(Path(tmp))
                    (skill_dir / "SKILL.md").write_text(
                        PLAIN_SKILL_MD + f"\nStore notes at {bad_path}\n", encoding="utf-8"
                    )
                    errors = self.validator.validate_skill(skill_dir, "plain")
                    self.assertTrue(
                        any("path" in e for e in errors),
                        f"expected a path error for {bad_path}, got {errors}",
                    )

    def test_pycache_and_pyc_files_are_not_scanned(self) -> None:
        # Bytecode caches embed absolute source paths; the validator must
        # ignore them so a generated skill's __pycache__ never yields a false
        # "hardcoded home path" violation.
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_plain_skill(Path(tmp))
            cache = skill_dir / "__pycache__"
            cache.mkdir()
            (cache / "module.cpython-312.pyc").write_text(
                "C:\\Users\\alice\\notes", encoding="utf-8", errors="ignore"
            )
            (skill_dir / "stray.pyc").write_text(
                "C:\\Users\\alice\\notes", encoding="utf-8", errors="ignore"
            )
            errors = self.validator.validate_skill(skill_dir, "plain")
            self.assertEqual(errors, [])

    def test_plain_mode_rejects_unknown_frontmatter_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_plain_skill(Path(tmp))
            (skill_dir / "SKILL.md").write_text(
                "---\nname: release-notes\ndescription: Use when drafting release notes.\ninterface:\n  display_name: Test\n---\n",
                encoding="utf-8",
            )
            errors = self.validator.validate_skill(skill_dir, "plain")
            self.assertTrue(any("unknown frontmatter field" in e for e in errors))

    def test_frontmatter_accepts_official_fields(self) -> None:
        # The validator must align with the official skill allow-list, so
        # license / allowed-tools / metadata are accepted; only fields outside
        # that set (e.g. interface) are rejected.
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_plain_skill(Path(tmp))
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: release-notes\n"
                "description: Use when drafting release notes.\n"
                "license: MIT\n"
                'allowed-tools: ["read"]\n'
                'metadata: {"a": 1}\n'
                "---\n",
                encoding="utf-8",
            )
            errors = self.validator.validate_skill(skill_dir, "plain")
            self.assertEqual(errors, [])

    def test_profile_mode_rejects_duplicate_dimensions(self) -> None:
        # uniqueItems on dimensions is enforced by the schema-driven check.
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_profile_skill(Path(tmp))
            document = _capability_document()
            document["dimensions"] = [document["dimensions"][0], dict(document["dimensions"][0])]
            (skill_dir / "schemas" / "profile-capability.json").write_text(
                json.dumps(document), encoding="utf-8"
            )
            errors = self.validator.validate_skill(skill_dir, "profile")
            self.assertTrue(any("unique" in e.lower() for e in errors))

    def test_json_file_id_fields_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_profile_skill(Path(tmp))
            (skill_dir / "references" / "profile-contract.md").write_text(
                PROFILE_CONTRACT_MD + '\nStore the receipt: "fileId": "abc123"\n',
                encoding="utf-8",
            )
            errors = self.validator.validate_skill(skill_dir, "profile")
            self.assertTrue(any("fileId" in e for e in errors))

    def test_drive_urls_and_write_apis_are_rejected(self) -> None:
        for needle in ["https://drive.google.com/file/d/xyz", "drive.files.create"]:
            with self.subTest(needle=needle):
                with tempfile.TemporaryDirectory() as tmp:
                    skill_dir = _write_profile_skill(Path(tmp))
                    (skill_dir / "references" / "profile-contract.md").write_text(
                        PROFILE_CONTRACT_MD + f"\nUse {needle} to persist.\n",
                        encoding="utf-8",
                    )
                    errors = self.validator.validate_skill(skill_dir, "profile")
                    self.assertTrue(
                        any("Drive" in e or "drive" in e for e in errors),
                        f"expected a Drive error for {needle}, got {errors}",
                    )

    def test_scaffold_tokens_are_rejected(self) -> None:
        for token in ["TODO", "TBD", "FIXME", "[insert the domain here]"]:
            with self.subTest(token=token):
                with tempfile.TemporaryDirectory() as tmp:
                    skill_dir = _write_profile_skill(Path(tmp))
                    (skill_dir / "SKILL.md").write_text(
                        PROFILE_SKILL_MD + f"\n{token}\n", encoding="utf-8"
                    )
                    errors = self.validator.validate_skill(skill_dir, "profile")
                    self.assertTrue(
                        any("scaffold" in e.lower() or "unfinished" in e.lower() for e in errors),
                        f"expected an unfinished-content error for {token}, got {errors}",
                    )

    def test_missing_skill_md_is_rejected_in_both_modes(self) -> None:
        for mode in ["plain", "profile"]:
            with self.subTest(mode=mode):
                with tempfile.TemporaryDirectory() as tmp:
                    skill_dir = _write_plain_skill(Path(tmp))
                    (skill_dir / "SKILL.md").unlink()
                    errors = self.validator.validate_skill(skill_dir, mode)
                    self.assertTrue(any("SKILL.md" in e for e in errors))

    def test_frontmatter_name_must_match_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_plain_skill(Path(tmp))
            (skill_dir / "SKILL.md").write_text(
                PLAIN_SKILL_MD.replace("name: release-notes", "name: other-name"),
                encoding="utf-8",
            )
            errors = self.validator.validate_skill(skill_dir, "plain")
            self.assertTrue(any("name" in e for e in errors))

    def test_checks_stay_within_supplied_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = _write_plain_skill(root)
            neighbor = root / "neighbor-skill"
            neighbor.mkdir()
            (neighbor / "SKILL.md").write_text(
                "TODO broken content outside the validated tree", encoding="utf-8"
            )
            errors = self.validator.validate_skill(skill_dir, "plain")
            self.assertEqual(errors, [])

    def test_path_escaping_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            skill_dir = _write_plain_skill(Path(tmp))
            escape = self._create_escape(skill_dir, Path(outside))
            if escape is None:
                self.skipTest("neither symlink nor junction creation is permitted on this machine")
            errors = self.validator.validate_skill(skill_dir, "plain")
            self.assertTrue(
                any("outside" in e for e in errors),
                f"expected an escape error, got {errors}",
            )

    @staticmethod
    def _create_escape(root: Path, outside: Path) -> Path | None:
        link = root / "escape"
        try:
            link.symlink_to(outside / "target.md")
            if link.is_symlink():
                return link
        except OSError:
            pass
        try:
            import _winapi
            _winapi.CreateJunction(str(outside), str(link))
            if link.exists():
                return link
        except (OSError, ImportError, AttributeError):
            pass
        return None

    def test_errors_are_stable_and_sorted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_profile_skill(Path(tmp))
            (skill_dir / "schemas" / "profile-capability.json").unlink()
            (skill_dir / "SKILL.md").write_text(
                PROFILE_SKILL_MD + "\nTODO leftover\n", encoding="utf-8"
            )
            first = self.validator.validate_skill(skill_dir, "profile")
            second = self.validator.validate_skill(skill_dir, "profile")
            self.assertEqual(first, second)
            self.assertEqual(first, sorted(first))

    def test_cli_returns_zero_for_valid_plain_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_plain_skill(Path(tmp))
            result = subprocess.run(
                [sys.executable, str(VALIDATOR_PATH), "--mode", "plain", str(skill_dir)],
                capture_output=True, text=True, cwd=str(SKILL_ROOT),
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_cli_returns_one_and_prints_errors_for_invalid_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_plain_skill(Path(tmp))
            (skill_dir / "SKILL.md").write_text("TODO: no frontmatter", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(VALIDATOR_PATH), "--mode", "plain", str(skill_dir)],
                capture_output=True, text=True, cwd=str(SKILL_ROOT),
            )
            self.assertEqual(result.returncode, 1)
            self.assertTrue(result.stdout.strip())


if __name__ == "__main__":
    unittest.main()
