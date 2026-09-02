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


if __name__ == "__main__":
    unittest.main()
