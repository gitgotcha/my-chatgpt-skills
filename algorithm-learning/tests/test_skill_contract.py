from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "references"

# Historical design documents are the only files allowed to describe the
# pre-normalisation layout, and only while they carry a superseded banner.
HISTORICAL_REFERENCES = sorted(REFERENCES.glob("2026-08-11-*.md"))

# Adjacent string literals keep the retired paths out of this file's own text,
# so the repository-wide scan cannot match the checker itself.
RETIRED_PATHS = (
    "algorithm/user" "s/",
    "profile/" "current",
    "profile/" "history",
    "practice" "/",
)
RETIRED_IDENTITY_GATE = r"identity\.(list|create|verify)"


def active_documents():
    candidates = [ROOT / "SKILL.md", ROOT / "agents" / "openai.yaml"]
    candidates += sorted(REFERENCES.glob("*.md"))
    candidates += sorted((ROOT / "tests").glob("*.py"))
    historical = {path.name for path in HISTORICAL_REFERENCES}
    return [path for path in candidates if path.name not in historical]


class AlgorithmLearningSkillContractTests(unittest.TestCase):
    def _read(self, filename):
        return (REFERENCES / filename).read_text(encoding="utf-8")

    def _skill(self):
        return (ROOT / "SKILL.md").read_text(encoding="utf-8")

    def test_skill_resolves_identity_by_name_instead_of_listing_users(self):
        skill = self._skill()
        for required in (
            "姓名",
            "submit_event",
            "userId",
            "解析",
            "注册",
        ):
            self.assertIn(required, skill)
        self.assertNotRegex(skill, RETIRED_IDENTITY_GATE)
        for removed in ("find_or_create_candidate", "list_candidates", "submit_artifact"):
            self.assertNotIn(removed, skill)

    def test_skill_keeps_answering_rules_and_event_evidence(self):
        skill = self._skill()
        for required in (
            "先诊断用户代码，再给最小修改版",
            "渐进提示",
            "algorithm-profile-contract.md",
            "学习事件",
            "algorithm.learning.completed",
        ):
            self.assertIn(required, skill)

    def test_contract_uses_canonical_plugin_root_and_global_registry(self):
        contract = self._read("algorithm-profile-contract.md")
        for required in (
            "my-chatGPT-skills/",
            "user-registry/registration-<userId>.json",
            "users/<userId>/algorithm/events/",
            "users/<userId>/algorithm/profile/snapshots/",
            "users/<userId>/algorithm/plans/daily/",
        ):
            self.assertIn(required, contract)

    def test_contract_defines_identity_event_and_snapshot_boundaries(self):
        contract = self._read("algorithm-profile-contract.md")
        for required in (
            "userId",
            "username",
            "registration-<userId>.json",
            "event-<eventId>.json",
            "sourceEventKeys",
            "不可跨用户读取",
        ):
            self.assertIn(required, contract)

    def test_append_only_contract_requires_unique_event_and_snapshot_files(self):
        contract = self._read("algorithm-profile-contract.md")
        for required in (
            "schemaVersion `1.2`",
            "event-<eventId>.json",
            "snapshot-<UTC>-<headEventId>.json",
            "sourceEventKeys",
        ):
            self.assertIn(required, contract)

    def test_worker_materializes_snapshots_from_verified_events(self):
        contract = self._read("algorithm-profile-contract.md")
        runtime = self._read("google-drive-runtime.md")
        for source in (contract, runtime):
            self.assertIn("submit_event", source)
        self.assertIn("Worker", contract)
        for required in (
            "Worker",
            "快照",
        ):
            self.assertIn(required, contract)

    def test_append_only_contract_keeps_legacy_files_read_only(self):
        contract = self._read("algorithm-profile-contract.md")
        runtime = self._read("google-drive-runtime.md")
        self.assertIn("旧文件保留作为只读兼容数据", contract)
        self.assertIn("禁止调用任何“更新文件内容”的接口", runtime)

    def test_daily_protocol_preserves_unfinished_work_and_aborts_on_drive_failure(self):
        protocol = self._read("algorithm-daily-protocol.md")
        for required in (
            "未完成题",
            "3～5",
            "不生成题单",
            "不宣称已同步画像",
            "追加式创建",
            "submit_event",
        ):
            self.assertIn(required, protocol)

    def test_daily_protocol_writes_plans_under_the_canonical_daily_folder(self):
        protocol = self._read("algorithm-daily-protocol.md")
        self.assertIn("plans/daily", protocol)
        self.assertIn("daily-plan-YYYY-MM-DD-<planId>.json", protocol)

    def test_scheduler_template_only_calls_the_skill_and_submit_event(self):
        template = self._read("daily-scheduler-prompt-template.md")
        for required in (
            "<USERNAME>",
            "algorithm-learning",
            "submit_event",
            "Asia/Shanghai",
            "DTSTART:20260101T090000",
        ):
            self.assertIn(required, template)
        # The scheduled task must never be told to touch Drive itself.
        self.assertNotIn("current snapshot", template)
        self.assertNotIn("Drive 根目录", template)

    def test_pending_status_distinguishes_event_from_snapshot_failure(self):
        skill = self._skill()
        self.assertIn("cloud_persistence_pending", skill)
        self.assertIn("profile_cache_pending", skill)

    def test_historical_documents_are_marked_superseded(self):
        self.assertEqual(4, len(HISTORICAL_REFERENCES))
        for path in HISTORICAL_REFERENCES:
            with self.subTest(path=path.name):
                head = path.read_text(encoding="utf-8").splitlines()[:6]
                banner = "\n".join(head)
                self.assertIn("Archived / superseded", banner)
                self.assertIn("MUST NOT be used for writes", banner)
                self.assertIn("algorithm-profile-contract.md", banner)

    def test_active_files_do_not_reference_retired_paths(self):
        identity_gate = re.compile(RETIRED_IDENTITY_GATE)
        for path in active_documents():
            with self.subTest(path=str(path.relative_to(ROOT))):
                text = path.read_text(encoding="utf-8")
                for retired in RETIRED_PATHS:
                    self.assertNotIn(retired, text)
                self.assertIsNone(identity_gate.search(text))


if __name__ == "__main__":
    unittest.main()
