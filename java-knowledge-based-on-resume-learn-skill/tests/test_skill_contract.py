from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "references"

# A skill may only ever persist through the MCP tool. Any instruction that
# reaches for the storage layer directly is a contract violation.
FORBIDDEN_DRIVE_WRITE = re.compile(
    r"(通过|使用|调用|借助)\s*Google\s*Drive[^\n]{0,30}(上传|写入|创建|覆盖|移动|删除)"
)
FORBIDDEN_SCHEDULER_WRITE = re.compile(
    r"(通过|使用|调用|运行)[^\n]{0,25}(cron|automation|scheduler)[^\n]{0,25}(创建|新建|设置|修改)"
)


def documents():
    return [ROOT / "SKILL.md", ROOT / "agents" / "openai.yaml"] + sorted(REFERENCES.glob("*.md"))


class JavaResumeKnowledgeSkillContractTests(unittest.TestCase):
    def _skill(self):
        return (ROOT / "SKILL.md").read_text(encoding="utf-8")

    def _read(self, filename):
        return (REFERENCES / filename).read_text(encoding="utf-8")

    def test_every_reference_exists(self):
        for filename in (
            "resume-evidence-policy.md",
            "question-bank-contract.md",
            "feedback-scoring-contract.md",
            "profile-storage-contract.md",
            "daily-task-prompt-template.md",
        ):
            self.assertTrue((REFERENCES / filename).is_file(), filename)
        self.assertTrue((ROOT / "agents" / "openai.yaml").is_file())

    # ---------------------------------------------------------------- modes

    def test_skill_declares_the_four_modes(self):
        skill = self._skill()
        for required in ("简历初始化", "逐题学习", "每日练习", "掌握度查看"):
            self.assertIn(required, skill)

    # ------------------------------------------------------------- identity

    def test_skill_resolves_the_user_by_name_through_submit_event(self):
        skill = self._skill()
        for required in ("姓名", "submit_event", "userId", "解析", "注册"):
            self.assertIn(required, skill)

    def test_skill_uses_the_canonical_plugin_root(self):
        for required in (
            "my-chatGPT-skills/",
            "users/<userId>/resume-knowledge/",
            "sources/resume/snapshots/",
            "question-bank/snapshots/",
            "profile/snapshots/",
            "plans/daily/",
        ):
            self.assertIn(required, self._read("profile-storage-contract.md"))

    # ------------------------------------------------------------- evidence

    def test_evidence_policy_defines_three_levels(self):
        evidence = self._read("resume-evidence-policy.md")
        for required in ("简历明示", "项目强推断", "无依据", "claim-confirmed", "claim-rejected"):
            self.assertIn(required, evidence)

    def test_evidence_policy_stops_without_a_resume(self):
        for document in (self._skill(), self._read("resume-evidence-policy.md")):
            self.assertIn("无简历", document)
            self.assertIn("停止", document)

    def test_evidence_policy_forbids_presenting_inference_as_project_fact(self):
        evidence = self._read("resume-evidence-policy.md")
        # A strong inference may be asked conditionally, but it must never be
        # reported as something the user actually did in the project.
        self.assertIn("条件式", evidence)
        self.assertRegex(
            evidence,
            r"(不得|禁止|不能)[^\n]{0,40}(断言|声称|冒充|当作|写成)[^\n]{0,30}(项目事实|实际使用|真实使用)",
        )

    # --------------------------------------------------------- question bank

    def test_question_bank_covers_the_java_backend_domains(self):
        bank = self._read("question-bank-contract.md")
        for required in ("Java", "MySQL", "Redis", "MQ", "中间件"):
            self.assertIn(required, bank)
        for required in ("questionKey", "knowledgePointId", "resumeVersion", "回答链", "评分点"):
            self.assertIn(required, bank)

    def test_question_key_is_semantically_stable(self):
        bank = self._read("question-bank-contract.md")
        self.assertIn("questionKey", bank)
        self.assertRegex(bank, r"(改写|改变|调整)[^\n]{0,12}表述[^\n]{0,40}(不得|不能|不产生)")

    # ------------------------------------------------------------- feedback

    def test_feedback_has_the_six_required_parts(self):
        feedback = self._read("feedback-scoring-contract.md")
        for required in ("总分", "维度", "已回答正确", "错误", "回答链", "参考回答", "掌握度"):
            self.assertIn(required, feedback)

    def test_scoring_uses_the_four_weighted_dimensions(self):
        feedback = self._read("feedback-scoring-contract.md")
        for required in ("技术正确性", "关键点完整性", "回答链路与层次", "简历场景结合度"):
            self.assertIn(required, feedback)
        for weight in ("40", "25", "20", "15"):
            self.assertIn(weight, feedback)
        self.assertIn("100", feedback)

    def test_scoring_points_stay_hidden_until_the_answer(self):
        feedback = self._read("feedback-scoring-contract.md")
        self.assertRegex(
            feedback,
            r"(作答|回答|答题)[^\n]{0,6}前[^\n]{0,40}(不得|禁止|不能)[^\n]{0,40}(评分点|参考答案|回答链)",
        )

    # ------------------------------------------------------------- mastery

    def test_mastery_uses_the_ewma_rule_and_once_per_day_scoring(self):
        storage = self._read("profile-storage-contract.md")
        for required in ("0.6", "0.4", "masteryScore", "localDate", "questionKey"):
            self.assertIn(required, storage)
        self.assertRegex(storage, r"(当天|当日|同日)[^\n]{0,30}(第一次|首次|只接受)")

    def test_daily_selection_prioritises_low_scores(self):
        template = self._read("daily-task-prompt-template.md")
        storage = self._read("profile-storage-contract.md")
        for document in (template, storage):
            self.assertIn("低分", document)
        self.assertIn("五题", storage)
        self.assertIn("去重", storage)

    def test_daily_plan_is_immutable_and_reused(self):
        storage = self._read("profile-storage-contract.md")
        self.assertRegex(storage, r"(已存在|已创建)[^\n]{0,30}(原样|不变|复用)")

    # --------------------------------------------------------- write access

    def test_submit_event_is_the_only_write_path(self):
        for path in documents():
            self.assertIn("submit_event", path.read_text(encoding="utf-8"), path.name)

    def test_no_document_writes_to_google_drive_directly(self):
        for path in documents():
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(FORBIDDEN_DRIVE_WRITE.search(text), f"{path.name}: {text}")

    def test_no_document_creates_scheduled_tasks(self):
        for path in documents():
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(FORBIDDEN_SCHEDULER_WRITE.search(text), path.name)

    def test_skill_states_that_the_user_owns_the_schedule(self):
        skill = self._skill()
        self.assertRegex(skill, r"(不得|不|禁止)[^\n]{0,20}(创建|建立|管理)[^\n]{0,10}定时任务")
        self.assertIn("用户自行", skill)

    def test_skill_accepts_the_scheduled_invocation_without_owning_it(self):
        template = self._read("daily-task-prompt-template.md")
        for required in ("Asia/Shanghai", "09:00", "用户自行"):
            self.assertIn(required, template)

    # ----------------------------------------------------------- boundaries

    def test_skill_stays_out_of_full_mock_interviews(self):
        skill = self._skill()
        self.assertIn("conducting-java-backend-mock-interviews", skill)
        self.assertIn("reviewing-java-backend-interviews", skill)


if __name__ == "__main__":
    unittest.main()
