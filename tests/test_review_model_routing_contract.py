from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "review-model-routing"


class ReviewModelRoutingContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

    def test_plain_skill_shape_and_metadata(self):
        frontmatter = self.skill.split("---", 2)[1]
        keys = set(re.findall(r"(?m)^([a-z_]+):", frontmatter))
        self.assertEqual(keys, {"name", "description"})
        self.assertRegex(frontmatter, r"(?m)^name: review-model-routing$")
        self.assertRegex(frontmatter, r"(?m)^description: Use when")
        self.assertNotIn("profile.", self.skill)
        for forbidden in (
            "schemas/profile-capability.json",
            "references/profile-contract.md",
            "tests/test_profile_contract.py",
        ):
            self.assertFalse((SKILL_ROOT / forbidden).exists(), forbidden)

    def test_progressive_disclosure_resources_exist(self):
        for relative in (
            "references/model-profiles.md",
            "references/review-block.md",
            "tests/behavior-scenarios.md",
        ):
            with self.subTest(relative=relative):
                path = SKILL_ROOT / relative
                self.assertTrue(path.is_file(), relative)
                self.assertTrue(path.read_text(encoding="utf-8").strip(), relative)
        self.assertIn("references/model-profiles.md", self.skill)
        self.assertIn("references/review-block.md", self.skill)

    def test_risk_and_gate_invariants_are_explicit(self):
        for token in (
            "light", "standard", "deep", "critical",
            "pre_implementation", "post_implementation",
            "pending", "blocked_model_config",
        ):
            self.assertIn(token, self.skill)
        review_block = (SKILL_ROOT / "references/review-block.md").read_text(
            encoding="utf-8"
        )
        for field in (
            "model:", "execution_mode:", "inputs:", "checks:",
            "pass_when:", "on_failure:", "on_unavailable:",
        ):
            self.assertIn(field, review_block)

    def test_light_review_defaults_to_luna(self):
        scenarios = (SKILL_ROOT / "tests/behavior-scenarios.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "For `light` review, select `gpt-5.6-luna` with `low` reasoning",
            self.skill,
        )
        self.assertIn(
            "Expected: `light`; reviewer `gpt-5.6-luna` with `low` reasoning",
            scenarios,
        )

    def test_behavior_scenarios_cover_risk_and_configuration_edges(self):
        scenarios = (SKILL_ROOT / "tests/behavior-scenarios.md").read_text(
            encoding="utf-8"
        )
        for case in (
            "copy-only", "tenant-isolation", "outbox-transaction",
            "missing-model-inventory", "existing-plan-change",
        ):
            self.assertIn(case, scenarios)

    def test_openai_adapter_allows_implicit_discovery(self):
        adapter = (SKILL_ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn('default_prompt: "Use $review-model-routing', adapter)
        self.assertIn("allow_implicit_invocation: true", adapter)


if __name__ == "__main__":
    unittest.main()
