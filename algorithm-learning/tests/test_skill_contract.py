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

    def test_new_conversation_requires_user_selection_before_answering(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "algorithm-profile-contract.md").read_text(
            encoding="utf-8"
        )
        for required in (
            "新算法对话的第一条学习请求",
            "A. 张三",
            "新建档案",
            "暂存",
            "不讲题",
        ):
            self.assertIn(required, skill)
        self.assertIn("user-index.json", contract)
        self.assertIn("仅允许为列出用户", contract)

    def test_answering_cycle_must_write_event_and_immediately_update_snapshot(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "algorithm-profile-contract.md").read_text(
            encoding="utf-8"
        )
        for required in (
            "每次算法学习请求结束前",
            "必须写入学习事件",
            "立即更新画像快照",
            "cloud_persistence_pending",
            "不得宣称已同步",
        ):
            self.assertIn(required, skill)
        self.assertIn("consulted", contract)
        self.assertIn("eventKey", contract)

    def test_bound_conversation_reuses_identity_until_explicit_switch(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for required in (
            "同一对话",
            "不重复询问身份",
            "切换用户",
            "重新验证身份",
            "清空本对话身份绑定",
        ):
            self.assertIn(required, skill)

    def test_daily_task_cannot_enumerate_other_users(self):
        protocol = (ROOT / "references" / "algorithm-daily-protocol.md").read_text(
            encoding="utf-8"
        )
        template = (ROOT / "references" / "daily-scheduler-prompt-template.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("不得读取 `user-index.json`", protocol)
        self.assertIn("不得读取 `user-index.json`", template)

    def test_identity_gate_plan_is_kept_with_mermaid_workflows(self):
        plan = (ROOT / "references" / "2026-08-11-conversation-identity-gate-plan.md").read_text(
            encoding="utf-8"
        )
        self.assertGreaterEqual(plan.count("```mermaid"), 2)
        self.assertIn("A. 张三", plan)
        self.assertIn("每次算法学习请求", plan)


if __name__ == "__main__":
    unittest.main()
