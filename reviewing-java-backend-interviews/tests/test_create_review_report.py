from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from docx import Document

from scripts.create_review_report import create_review_report


class ReviewReportTests(unittest.TestCase):
    def test_creates_readable_report_with_profile_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            source = directory / "review.json"
            output = directory / "review-report.docx"
            source.write_text(
                json.dumps(
                    {
                        "basic_info": {"candidate": "候选人", "completed": False},
                        "record_quality": {"overall_confidence": 0.8},
                        "overall_assessment": {"summary": "需要补强缓存一致性。"},
                        "scores": [{"dimension": "技术正确性", "score": 14, "comment": "部分正确"}],
                        "questions": [{
                            "question": "Redis 缓存一致性",
                            "live_answer": "删除缓存",
                            "retrospective_answer": "事后补充：双删策略",
                            "confidence": "高",
                        }],
                        "profile_updates": ["W001：待验证弱点"],
                        "next_interview_guidance": {"primary_goals": ["复测缓存一致性"]},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            create_review_report(source, output)

            document = Document(output)
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
            self.assertTrue(output.exists())
            self.assertIn("原始记录说明与可信度", text)
            self.assertIn("能力画像变化", text)
            self.assertIn("下一次模拟面试出题指南", text)
            self.assertIn("目录", text)
            self.assertIn("事后补充", text)
            self.assertIn("PAGE", document.sections[0].footer._element.xml)

    def test_renders_identity_source_and_profile_change_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            source = directory / "review.json"
            output = directory / "review-report.docx"
            source.write_text(
                json.dumps(
                    {
                        "basic_info": {
                            "candidate": "测试候选人",
                            "candidate_id": "TEST-20260806-001",
                            "interview_type": "真实面试",
                            "session_id": "REAL-20260806-001",
                            "review_version": 1,
                        },
                        "profile_change_summary": ["W-001：待验证"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            create_review_report(source, output)

            document = Document(output)
            text = "\n".join(
                paragraph.text for paragraph in document.paragraphs
            ) + "\n" + "\n".join(
                cell.text for table in document.tables for row in table.rows for cell in row.cells
            )
            self.assertIn("TEST-20260806-001", text)
            self.assertIn("真实面试", text)
            self.assertIn("画像变化摘要", text)
