from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "references"
HISTORICAL_REFERENCES = sorted(REFERENCES.glob("2026-08-11-*.md"))


def active_documents():
    candidates = [ROOT / "SKILL.md", ROOT / "README.md", ROOT / "agents" / "openai.yaml"]
    candidates += sorted(REFERENCES.glob("*.md"))
    historical = {path.name for path in HISTORICAL_REFERENCES}
    return [path for path in candidates if path.name not in historical]


class AlgorithmLearningSkillContractTests(unittest.TestCase):
    def read(self, path):
        return path.read_text(encoding="utf-8")

    def test_skill_uses_readable_rds_snapshot_routes(self):
        skill = self.read(ROOT / "SKILL.md")
        self.assertIn("rds", skill)
        self.assertIn("knowledge/algorithm-learning/学习快照.json", skill)
        self.assertIn("algorithm-profile-contract.md", skill)
        self.assertNotIn("submit_event", skill)
        self.assertNotIn("user.resolve", skill)
        self.assertNotIn("UUID", skill)

    def test_snapshot_contract_keeps_evidence_neutral_and_append_only(self):
        contract = self.read(REFERENCES / "algorithm-profile-contract.md")
        for required in (
            "algorithm-learning-snapshot/1",
            '"records"',
            '"dailyPlans"',
            "consulted",
            "不得臆测弱点",
            "RDS-JBryon",
        ):
            with self.subTest(required=required):
                self.assertIn(required, contract)
        for retired in ("userId", "submit_event", "Drive", "identityResolveEvent"):
            with self.subTest(retired=retired):
                self.assertNotIn(retired, contract)

    def test_daily_protocol_preserves_plans_and_reads_the_snapshot(self):
        protocol = self.read(REFERENCES / "algorithm-daily-protocol.md")
        for required in ("knowledge/algorithm-learning/学习快照.json", "未完成题", "3–5", "7 天内", "不覆盖"):
            with self.subTest(required=required):
                self.assertIn(required, protocol)
        self.assertNotIn("D1 Outbox", protocol)
        self.assertNotIn("submit_event", protocol)

    def test_scheduler_template_delegates_persistence_to_the_skill(self):
        template = self.read(REFERENCES / "daily-scheduler-prompt-template.md")
        self.assertIn("algorithm-learning", template)
        self.assertIn("Asia/Shanghai", template)
        self.assertIn("rds MCP", template)
        self.assertNotIn("submit_event", template)
        self.assertNotIn("Drive 根目录", template)

    def test_historical_documents_are_marked_superseded(self):
        self.assertGreaterEqual(len(HISTORICAL_REFERENCES), 4)
        for path in HISTORICAL_REFERENCES:
            with self.subTest(path=path.name):
                banner = "\n".join(self.read(path).splitlines()[:6])
                self.assertIn("Archived / superseded", banner)
                self.assertIn("MUST NOT be used for writes", banner)

    def test_active_documents_do_not_route_to_the_retired_service(self):
        patterns = re.compile(r"(?:submit_event|user\.resolve|identity\.(?:list|create|verify)|rds-v2-runtime\.md|RDS V2 运行契约)")
        for path in active_documents():
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                self.assertIsNone(patterns.search(self.read(path)))


if __name__ == "__main__":
    unittest.main()
