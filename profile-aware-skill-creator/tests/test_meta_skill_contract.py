"""Static contract tests for the profile-aware-skill-creator meta Skill.

These tests use only the Python standard library. They parse the real files
shipped with the meta Skill and assert the invariants required by the
implementation plan.

Run from ``profile-aware-skill-creator``::

    python -m unittest tests.test_meta_skill_contract -v
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = SKILL_ROOT / "schemas" / "profile-capability.schema.json"

REQUIRED_TOP_LEVEL = [
    "schemaVersion",
    "domain",
    "sourceSkill",
    "dimensions",
    "evidencePolicy",
    "runtime",
    "portability",
]

RESERVED_DOMAINS = ["algorithm", "interview", "resume-knowledge", "system", "profile"]

ALLOWED_OUTCOMES = [
    "observed",
    "consulted",
    "stuck",
    "incorrect",
    "partial",
    "completed",
    "correct",
    "passed",
    "failed",
]

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

VALID_INSTANCE = {
    "schemaVersion": "1.0",
    "domain": "english-learning",
    "sourceSkill": "english-learning",
    "dimensions": [
        {
            "dimensionKey": "vocabulary",
            "subjectKeyDescription": "被观察的单词或短语的稳定键",
            "description": "词汇理解与主动使用能力",
        }
    ],
    "evidencePolicy": {
        "recordWhen": [
            "用户给出可核验答案、尝试或明确表示卡住"
        ],
        "doNotRecordWhen": [
            "只有模型推测而没有用户可观察行为"
        ],
        "allowedOutcomes": ALLOWED_OUTCOMES,
        "sourceRefPolicy": "每条独立证据使用稳定且可区分的来源引用",
        "minimumEvidenceTextLength": 8,
    },
    "runtime": dict(RUNTIME_OPERATIONS),
    "portability": {
        "platforms": list(PLATFORMS),
        "coreContractDependsOnOpenaiYaml": False,
    },
}


def _invalid_variant(**changes: object) -> dict:
    """Deep-copy the valid instance and apply top-level changes."""
    instance = json.loads(json.dumps(VALID_INSTANCE))
    for key, value in changes.items():
        if value is None:
            instance.pop(key, None)
        else:
            instance[key] = value
    return instance


# Invalid-case fixtures consumed by the validator behavior tests in Task 6.
INVALID_RESERVED_DOMAIN = _invalid_variant(domain="algorithm")
INVALID_EMPTY_DIMENSIONS = _invalid_variant(dimensions=[])
INVALID_ALTERED_EVENT_NAME = _invalid_variant(
    runtime={
        **RUNTIME_OPERATIONS,
        "profileReadEvent": "profile.snapshot.fetch",
    }
)
INVALID_DIRECT_DRIVE_ACCESS = _invalid_variant(
    runtime={
        **RUNTIME_OPERATIONS,
        "directDriveAccess": True,
    }
)
INVALID_MISSING_EVIDENCE_POLICIES = _invalid_variant(
    evidencePolicy={"recordWhen": ["用户给出可核验答案"]}
)


class ProfileCapabilitySchemaTest(unittest.TestCase):
    """Contract of ``schemas/profile-capability.schema.json``."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_schema_parses_and_declares_draft_2020_12(self) -> None:
        self.assertEqual(
            self.schema["$schema"],
            "https://json-schema.org/draft/2020-12/schema",
        )

    def test_required_top_level_fields_are_exact(self) -> None:
        self.assertEqual(
            sorted(self.schema["required"]),
            sorted(REQUIRED_TOP_LEVEL),
        )
        self.assertEqual(
            sorted(self.schema["properties"].keys()),
            sorted(REQUIRED_TOP_LEVEL),
        )

    def test_domain_pattern_and_reserved_names(self) -> None:
        domain = self.schema["properties"]["domain"]
        self.assertEqual(
            domain["pattern"],
            "^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$",
        )
        self.assertEqual(domain["not"]["enum"], RESERVED_DOMAINS)

    def test_runtime_operation_names_and_direct_drive_access_are_constants(self) -> None:
        runtime = self.schema["properties"]["runtime"]
        self.assertEqual(
            sorted(runtime["required"]),
            sorted(RUNTIME_OPERATIONS.keys()),
        )
        for key, value in RUNTIME_OPERATIONS.items():
            self.assertEqual(
                runtime["properties"][key]["const"],
                value,
                f"runtime.{key} must be the constant {value!r}",
            )

    def test_platform_list_and_openai_yaml_independence_are_constants(self) -> None:
        portability = self.schema["properties"]["portability"]
        self.assertEqual(portability["properties"]["platforms"]["const"], PLATFORMS)
        self.assertEqual(
            portability["properties"]["coreContractDependsOnOpenaiYaml"]["const"],
            False,
        )

    def test_evidence_policy_shape(self) -> None:
        evidence = self.schema["properties"]["evidencePolicy"]
        self.assertEqual(
            sorted(evidence["required"]),
            sorted(
                [
                    "recordWhen",
                    "doNotRecordWhen",
                    "allowedOutcomes",
                    "sourceRefPolicy",
                    "minimumEvidenceTextLength",
                ]
            ),
        )
        self.assertEqual(
            evidence["properties"]["allowedOutcomes"]["const"],
            ALLOWED_OUTCOMES,
        )

    def test_valid_instance_has_every_required_field(self) -> None:
        for key in REQUIRED_TOP_LEVEL:
            self.assertIn(key, VALID_INSTANCE)

    def test_valid_instance_matches_schema_constants(self) -> None:
        self.assertEqual(VALID_INSTANCE["schemaVersion"], "1.0")
        self.assertEqual(VALID_INSTANCE["runtime"], RUNTIME_OPERATIONS)
        self.assertEqual(
            VALID_INSTANCE["evidencePolicy"]["allowedOutcomes"],
            ALLOWED_OUTCOMES,
        )
        self.assertEqual(
            VALID_INSTANCE["portability"]["platforms"],
            PLATFORMS,
        )
        self.assertIs(
            VALID_INSTANCE["portability"]["coreContractDependsOnOpenaiYaml"],
            False,
        )
        self.assertNotIn(VALID_INSTANCE["domain"], RESERVED_DOMAINS)


PROFILE_AUTHORING_STANDARD = SKILL_ROOT / "references" / "profile-authoring-standard.md"
SUBMIT_EVENT_RUNTIME = SKILL_ROOT / "references" / "submit-event-runtime.md"
PORTABLE_SKILL_STANDARD = SKILL_ROOT / "references" / "portable-skill-standard.md"

REFERENCE_FILES = {
    "profile-authoring-standard.md": PROFILE_AUTHORING_STANDARD,
    "submit-event-runtime.md": SUBMIT_EVENT_RUNTIME,
    "portable-skill-standard.md": PORTABLE_SKILL_STANDARD,
}

# The five logical operations of the generic profile protocol.
PROFILE_OPERATIONS = [
    "system.capabilities.read",
    "system.user.resolve",
    "system.user-registered",
    "profile.snapshot.read",
    "profile.evidence.recorded",
]

# Exact target file sets.
PLAIN_FORBIDDEN_PATHS = [
    "references/profile-contract.md",
    "schemas/profile-capability.json",
    "tests/test_profile_contract.py",
]
PROFILE_REQUIRED_PATHS = [
    "references/profile-contract.md",
    "schemas/profile-capability.json",
    "tests/test_profile_contract.py",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class ReferencesExistTest(unittest.TestCase):
    """All three progressive-disclosure references must ship with the Skill."""

    def test_all_references_exist(self) -> None:
        for name, path in REFERENCE_FILES.items():
            self.assertTrue(path.is_file(), f"missing reference: {name}")
            self.assertGreater(len(_read(path)), 500, f"{name} is too small to be useful")


class ProfileAuthoringStandardTest(unittest.TestCase):
    """Behavioral contract of ``references/profile-authoring-standard.md``."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = _read(PROFILE_AUTHORING_STANDARD)

    def test_documents_authoring_decision_record_in_order(self) -> None:
        steps = [
            "resolved target directory",
            "plain/profile choice",
            "reserved names",
            "sourceSkill",
            "dimensions",
            "recordWhen",
            "minimal added files",
            "validation mode",
        ]
        positions = [self.text.lower().find(step.lower()) for step in steps]
        for position, step in zip(positions, steps):
            self.assertGreater(position, -1, f"decision-record step missing: {step}")
        self.assertEqual(
            positions,
            sorted(positions),
            "decision-record steps must appear in the documented order",
        )

    def test_capability_file_is_not_the_runtime_capability_event(self) -> None:
        self.assertIn("profile-capability.json", self.text)
        self.assertIn("system.capabilities.read", self.text)
        self.assertIn("cannot substitute", self.text)

    def test_safe_domain_rules_match_schema(self) -> None:
        self.assertIn("^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$", self.text)
        for reserved in RESERVED_DOMAINS:
            self.assertIn(reserved, self.text)

    def test_evidence_collection_rules(self) -> None:
        for outcome in ["observed", "stuck", "partial", "correct"]:
            self.assertIn(outcome, self.text)
        self.assertIn("recordWhen", self.text)
        self.assertIn("doNotRecordWhen", self.text)

    def test_exact_target_file_sets(self) -> None:
        for path in PROFILE_REQUIRED_PATHS:
            self.assertIn(path, self.text)
        self.assertIn("must not", self.text.lower())

    def test_preservation_rules_for_existing_directories(self) -> None:
        self.assertIn("existing", self.text.lower())
        self.assertIn("preserve", self.text.lower())
        self.assertIn("unrelated", self.text.lower())

    def test_contract_test_requirements_list_four_behaviors(self) -> None:
        lowered = self.text.lower()
        # The generated contract test must cover all four runtime behaviors.
        self.assertIn("capability preflight", lowered)
        self.assertIn("user consent", lowered)
        self.assertIn("immutable", lowered)
        self.assertIn("preservation", lowered)
        self.assertIn("placeholder", lowered)


class SubmitEventRuntimeTest(unittest.TestCase):
    """Behavioral contract of ``references/submit-event-runtime.md``."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = _read(SUBMIT_EVENT_RUNTIME)

    def test_contains_concrete_envelopes_for_all_five_operations(self) -> None:
        for operation in PROFILE_OPERATIONS:
            self.assertIn(f'"eventType": "{operation}"', self.text,
                          f"missing concrete envelope for {operation}")

    def test_envelope_versions_are_documented(self) -> None:
        self.assertIn('"schemaVersion": "1.2"', self.text)
        self.assertIn('"schemaVersion": "1.0"', self.text)

    def test_runtime_sequence_is_documented_in_order(self) -> None:
        start = self.text.find("## Runtime sequence")
        end = self.text.find("## Operation 1", start)
        section = self.text[start:end]
        self.assertGreater(start, -1, "runtime sequence section missing")
        sequence = [
            "system.capabilities.read",
            "system.user.resolve",
            "system.user-registered",
            "profile.snapshot.read",
            "profile.evidence.recorded",
        ]
        positions = [section.find(step) for step in sequence]
        for position, step in zip(positions, sequence):
            self.assertGreater(position, -1, f"sequence step missing: {step}")
        self.assertEqual(
            positions,
            sorted(positions),
            "runtime sequence must be documented in order",
        )

    def test_async_receipt_wording_without_drive_fileid_promise(self) -> None:
        self.assertIn("pending", self.text)
        self.assertIn("cloud_accepted", self.text)
        self.assertIn("fileId", self.text)
        self.assertIn("must not", self.text.lower())

    def test_identical_envelopes_across_platforms(self) -> None:
        lowered = self.text.lower()
        for platform in PLATFORMS:
            self.assertIn(platform.lower(), lowered)
        self.assertIn("identical", lowered)

    def test_fail_closed_when_capability_or_identity_unavailable(self) -> None:
        self.assertIn("unsupported_capability", self.text)
        self.assertIn("identity_not_found", self.text)
        self.assertIn("fail", self.text.lower())

    def test_error_semantics_documented(self) -> None:
        for error in [
            "user_conflict",
            "identity_mismatch",
            "invalid_domain",
            "invalid_profile_event",
            "event_key_conflict",
            "target_event_not_found",
            "target_event_inactive",
        ]:
            self.assertIn(error, self.text)

    def test_no_direct_drive_access_or_snapshot_overwrite(self) -> None:
        self.assertIn("submit_event", self.text)
        self.assertIn("Google Drive connector", self.text)
        self.assertIn("overwrite", self.text.lower())

    def test_correction_examples_follow_rules(self) -> None:
        self.assertIn("supersede", self.text)
        self.assertIn("invalidate", self.text)
        self.assertIn("targetEventKey", self.text)
        self.assertIn("evidenceRefs", self.text)

    def test_no_personal_absolute_paths_or_drive_ids(self) -> None:
        for forbidden in [
            "C:\\Users\\",
            "/Users/",
            "/home/",
            "/root/",
            "drive.google.com",
        ]:
            self.assertNotIn(forbidden, self.text)


class PortableSkillStandardTest(unittest.TestCase):
    """Behavioral contract of ``references/portable-skill-standard.md``."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = _read(PORTABLE_SKILL_STANDARD)

    def test_base_skill_shape(self) -> None:
        self.assertIn("SKILL.md", self.text)
        self.assertIn("name", self.text)
        self.assertIn("description", self.text)
        self.assertIn("progressive disclosure", self.text.lower())
        self.assertIn("hyphen", self.text.lower())

    def test_target_path_authority(self) -> None:
        lowered = self.text.lower()
        self.assertTrue(
            "target path" in lowered or "target-path" in lowered,
            "target path authority must be documented",
        )
        self.assertIn("authorit", lowered)

    def test_update_in_place_preservation(self) -> None:
        self.assertIn("update", self.text.lower())
        self.assertIn("preserv", self.text.lower())

    def test_deterministic_validation(self) -> None:
        self.assertIn("validation", self.text.lower())
        self.assertIn("deterministic", self.text.lower())

    def test_routing_to_skill_creator_when_available(self) -> None:
        self.assertIn("$skill-creator", self.text)

    def test_openai_yaml_is_optional_adapter(self) -> None:
        self.assertIn("agents/openai.yaml", self.text)
        self.assertIn("optional", self.text.lower())

    def test_platform_syntax_differs_but_envelope_identical(self) -> None:
        lowered = self.text.lower()
        for platform in PLATFORMS:
            self.assertIn(platform.lower(), lowered)
        self.assertIn("envelope", lowered)

    def test_no_personal_absolute_paths_or_drive_ids(self) -> None:
        for forbidden in [
            "C:\\Users\\",
            "/Users/",
            "/home/",
            "/root/",
            "drive.google.com",
        ]:
            self.assertNotIn(forbidden, self.text)


SKILL_MD = SKILL_ROOT / "SKILL.md"
OPENAI_YAML = SKILL_ROOT / "agents" / "openai.yaml"


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse the small YAML frontmatter block without PyYAML."""
    if not text.startswith("---\n"):
        raise ValueError("missing frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("unterminated frontmatter")
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, text[end + 5:]


class MetaSkillEntrypointTest(unittest.TestCase):
    """Observable invariants of the meta Skill entrypoint."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = _read(SKILL_MD)
        cls.frontmatter, cls.body = _parse_frontmatter(cls.text)
        cls.yaml_text = _read(OPENAI_YAML)

    def test_frontmatter_name_equals_folder_name(self) -> None:
        self.assertEqual(self.frontmatter.get("name"), "profile-aware-skill-creator")
        self.assertEqual(SKILL_ROOT.name, "profile-aware-skill-creator")

    def test_description_begins_with_use_when(self) -> None:
        self.assertTrue(
            self.frontmatter.get("description", "").startswith("Use when"),
            "description must begin with 'Use when'",
        )

    def test_explicit_only_policy(self) -> None:
        self.assertIn("allow_implicit_invocation: false", self.yaml_text)

    def test_default_prompt_references_the_skill(self) -> None:
        self.assertIn("$profile-aware-skill-creator", self.yaml_text)

    def test_body_is_concise(self) -> None:
        words = len(self.body.split())
        self.assertLessEqual(words, 500, f"SKILL.md body too long: {words} words")

    def test_body_has_no_json_examples(self) -> None:
        self.assertNotIn('"schemaVersion"', self.body)
        self.assertNotIn("eventType", self.body)

    def test_target_path_required_and_preserved(self) -> None:
        lowered = self.body.lower()
        self.assertIn("target", lowered)
        self.assertIn("path", lowered)
        self.assertIn("preserv", lowered)
        self.assertIn("inspect", lowered)

    def test_no_design_approval_when_sufficient_but_ask_when_missing(self) -> None:
        """Regression from ca26e16 — made conditional per user ruling.

        When the target path, the routing answer, and sufficient requirements
        are already known, the agent must not stop to request design approval.
        But when a genuinely necessary input is missing (e.g., the target path
        was not specified), the agent may ask for it. The unconditional "never
        request design approval" was too absolute and blocked legitimate asks.
        """
        # Collapse whitespace: the guidance may wrap across source lines.
        flattened = " ".join(self.body.lower().split())
        # The routing question is still the only routing question.
        self.assertIn("only", flattened)
        self.assertIn("routing question", flattened)
        # Design approval is still forbidden — but conditionally.
        self.assertIn("approval", flattened)
        # The condition: sufficient requirements for safe implementation are known.
        self.assertIn("sufficient", flattened)
        # The exception: missing necessary input may be asked for.
        self.assertIn("missing", flattened)

    def test_frontmatter_contract_is_not_overridable_by_an_initializer(self) -> None:
        """Regression from the GREEN forward test, case 2 (fresh agent).

        The plain branch tells the agent to invoke the platform's own
        ``$skill-creator`` when it is available. A fresh agent did exactly
        that, and the external initializer produced ``name: release-notes``
        inside a folder named ``plain-release-notes`` plus a description that
        did not begin with ``Use when`` -- both invalid under this project's
        validator. The contract must be stated as applying to whichever
        initializer ran, not only to the portable standard path.
        """
        lowered = self.body.lower()
        self.assertIn("initializer", lowered)
        self.assertIn("folder name", lowered)
        self.assertIn("use when", lowered)

    def test_prose_skill_name_becomes_display_name_not_a_folder_rename(self) -> None:
        """The folder name stays the identifier when the prose names differ."""
        # Collapse whitespace: the guidance may wrap "never rename" across lines.
        flattened = " ".join(self.body.lower().split())
        self.assertIn("display_name", self.body)
        self.assertIn("never rename", flattened)

    def test_display_name_is_adapter_only_not_skill_frontmatter(self) -> None:
        """display_name must never be emitted in SKILL.md frontmatter."""
        lowered = " ".join(self.body.lower().split())
        self.assertIn("interface.display_name", self.body)
        self.assertIn("agents/openai.yaml", lowered)
        self.assertIn("frontmatter", lowered)
        self.assertIn("only", lowered)
        self.assertRegex(lowered, r"omit|omitted|without")

    def test_interface_key_is_forbidden_in_skill_frontmatter(self) -> None:
        """Regression from the final-review finding (Case 3).

        A fresh agent emitted an ``interface:`` block inside SKILL.md
        frontmatter, which the official validator rejects (exit 1). The
        guidance must state, in so many words, that no other key -- including
        ``interface`` or ``display_name`` -- may appear in SKILL.md
        frontmatter; otherwise a literal reading of "interface.display_name"
        leads agents to write it there.
        """
        lowered = " ".join(self.body.lower().split())
        self.assertIn("interface", lowered)
        self.assertIn("frontmatter", lowered)
        # A strong, unambiguous prohibition must be present.
        self.assertIn("no other key", lowered)
        self.assertRegex(lowered, r"no other key.{0,120}interface")

    def test_named_directory_is_the_skill_root_not_a_nested_subdirectory(self) -> None:
        """Regression from the GREEN forward test, case 2.

        Saying only "never redirect to another location" was not enough: the
        generator still created ``<target>/<skill-name>/SKILL.md`` instead of
        ``<target>/SKILL.md``. The guidance must name the Skill root and
        forbid a nested subdirectory explicitly.
        """
        for label, text in (
            ("SKILL.md", self.body),
            ("portable-skill-standard.md", _read(PORTABLE_SKILL_STANDARD)),
        ):
            lowered = text.lower()
            self.assertIn(
                "skill root",
                lowered,
                f"{label} must state which directory is the Skill root",
            )
            self.assertIn(
                "nested",
                lowered,
                f"{label} must forbid nested output directories",
            )
            self.assertIn(
                "subdirector",
                lowered,
                f"{label} must forbid generating into a subdirectory",
            )

    def test_profile_question_gates_two_exclusive_branches(self) -> None:
        lowered = self.body.lower()
        self.assertIn("profile", lowered)
        self.assertIn("question", lowered)
        self.assertIn("plain", lowered)
        # Two mutually exclusive branches, never both triggered by one answer.
        self.assertIn("plain", lowered)
        self.assertIn("profile", lowered)

    def test_plain_mode_routes_to_skill_creator_and_forbids_profile_artifacts(self) -> None:
        self.assertIn("$skill-creator", self.body)
        for path in PLAIN_FORBIDDEN_PATHS:
            self.assertIn(path, self.body)

    def test_profile_mode_reads_references_and_produces_three_files(self) -> None:
        for path in PROFILE_REQUIRED_PATHS:
            self.assertIn(path, self.body)
        self.assertIn("profile-authoring-standard.md", self.body)
        self.assertIn("submit-event-runtime.md", self.body)
        self.assertIn("validate", self.body.lower())

    def test_profile_branch_requires_four_contract_behaviors(self) -> None:
        lowered = self.body.lower()
        # The profile branch must require the contract tests to actually run
        # and cover the four runtime behaviors; a placeholder is rejected.
        for token in (
            "capability preflight",
            "user consent",
            "immutable",
            "full scan",
            "placeholder",
        ):
            self.assertIn(token, lowered)

    def test_creation_time_performs_no_profile_mcp_operations(self) -> None:
        # Creating a Skill must not itself call identity/profile operations.
        for operation in [
            "system.user.resolve",
            "system.user-registered",
            "profile.snapshot.read",
            "profile.evidence.recorded",
        ]:
            self.assertNotIn(operation, self.body)

    def test_no_codex_adapter_is_normative_for_other_platforms(self) -> None:
        lowered = self.body.lower()
        self.assertIn("portable-skill-standard.md", self.body)
        self.assertNotIn("openai.yaml", lowered.replace("agents/openai.yaml", ""))

    def test_yaml_display_metadata(self) -> None:
        self.assertIn("display_name", self.yaml_text)
        self.assertIn("short_description", self.yaml_text)
        self.assertIn("default_prompt", self.yaml_text)


if __name__ == "__main__":
    unittest.main()
