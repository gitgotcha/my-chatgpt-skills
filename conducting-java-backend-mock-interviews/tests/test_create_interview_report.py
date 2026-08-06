from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from docx import Document

from scripts.create_interview_report import create_report


class ReportGenerationTests(unittest.TestCase):
    def test_creates_readable_report_with_core_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            source = temporary_path / "record.json"
            output = temporary_path / "report.docx"
            source.write_text(
                json.dumps(
                    {
                        "basic_info": {
                            "candidate": "候选人",
                            "focus_project": "订单系统",
                            "completed": False,
                        },
                        "conclusion": {
                            "result": "边缘通过",
                            "score": 72,
                            "summary": "项目熟悉，缓存一致性需补强。",
                        },
                        "scores": [
                            {"dimension": "技术正确性", "score": 15, "comment": "基础扎实"}
                        ],
                        "questions": [
                            {
                                "id": 1,
                                "question": "介绍订单系统",
                                "answer_summary": "负责下单链路",
                                "evaluation": "职责较清晰",
                                "standard_answer": "按 STAR 说明。",
                                "spoken_answer": "我负责……",
                                "expression_feedback": "先给结论",
                                "next_questions": ["事务边界在哪里？"],
                            }
                        ],
                        "training_plan": {"immediate": ["缓存一致性"]},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            create_report(source, output)

            document = Document(output)
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
            self.assertTrue(output.exists())
            self.assertIn("Java 后端模拟面试报告", text)
            self.assertIn("逐题复盘", text)

    def test_rejects_pending_mock_handoff_without_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            source = temporary_path / "pending.json"
            output = temporary_path / "report.docx"
            source.write_text(
                json.dumps(
                    {
                        "state": "review_pending",
                        "candidate_id": "TEST-20260806-001",
                        "session_id": "MOCK-20260806-001",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                create_report(source, output)
