from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AlgorithmLearningSkillContractTests(unittest.TestCase):
    def test_skill_keeps_answering_rules_and_routes_profile_events(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for required in (
            "先诊断用户代码，再给最小修改版",
            "渐进提示",
            "algorithm-profile-contract.md",
            "学习事件",
            "userId",
        ):
            self.assertIn(required, skill)

    def test_profile_contract_defines_identity_event_and_snapshot_boundaries(self):
        contract = (ROOT / "references" / "algorithm-profile-contract.md").read_text(
            encoding="utf-8"
        )
        for required in (
            "userId",
            "username",
            "event-log.jsonl",
            "profile-snapshot.json",
            "profileVersion",
            "不可跨用户读取",
        ):
            self.assertIn(required, contract)

    def test_daily_protocol_preserves_unfinished_work_and_aborts_on_drive_failure(self):
        protocol = (ROOT / "references" / "algorithm-daily-protocol.md").read_text(
            encoding="utf-8"
        )
        for required in (
            "未完成题",
            "3～5",
            "不生成题单",
            "不更新镜像",
            "原子",
        ):
            self.assertIn(required, protocol)

    def test_scheduler_template_is_identity_locked_and_has_nine_am_schedule(self):
        template = (ROOT / "references" / "daily-scheduler-prompt-template.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("<USER_UUID>", template)
        self.assertIn("<USERNAME>", template)
        self.assertIn("Asia/Shanghai", template)
        self.assertIn("DTSTART:20260101T090000", template)


if __name__ == "__main__":
    unittest.main()
