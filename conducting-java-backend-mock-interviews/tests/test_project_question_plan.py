"""Contract tests for the pure project/mock question-plan selector.

Run from the skill root::

    python -m unittest discover -s tests -v

The selector owns composition only: it never calls a model, the network, the
filesystem or RDS.  Candidate semantics stay with the caller (see
``references/project-targeted-interview.md``).
"""

from __future__ import annotations

import copy
import unittest

from scripts.project_question_plan import (
    QuestionPlanError,
    build_question_plan,
    resolve_target_project,
    validate_project_alias,
)


PROJECT_A = "11111111-1111-4111-8111-111111111111"
PROJECT_B = "22222222-2222-4222-8222-222222222222"


def _candidate(number: int, *, source: str = "domain_knowledge", project_id: str | None = None, **overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "candidateId": f"C-{number:03d}",
        "source": source,
        "projectId": project_id,
        "questionKey": f"question-{number:03d}",
        "variantId": f"variant-{number:03d}",
        "level": "L2",
        "originGroupId": f"origin-{number:03d}",
    }
    value.update(overrides)
    return value


def _weakness(number: int, *, project_id: str | None = None, **overrides: object) -> dict[str, object]:
    return _candidate(
        number,
        source="history_weakness",
        project_id=project_id,
        weaknessId=f"W-{number:03d}",
        **overrides,
    )


def _sources(plan: dict[str, list[dict[str, object]]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in plan["selected"]:
        source = str(item["source"])
        counts[source] = counts.get(source, 0) + 1
    return counts


def _rejection_reasons(plan: dict[str, list[dict[str, object]]]) -> list[str]:
    return [str(item["reason"]) for item in plan["rejected"]]


def _warning_codes(plan: dict[str, list[dict[str, object]]]) -> list[str]:
    return [str(item["code"]) for item in plan["warnings"]]


class FullMockCompositionTests(unittest.TestCase):
    def test_full_mock_keeps_the_documented_source_mix(self) -> None:
        candidates: list[dict[str, object]] = []
        number = 0
        for source, count in (
            ("resume_project", 11),
            ("history_weakness", 3),
            ("domain_knowledge", 2),
            ("algorithm_scenario", 4),
        ):
            for _ in range(count):
                number += 1
                candidates.append(_candidate(number, source=source))

        plan = build_question_plan(
            mode="full_mock",
            resume_claims=["R-1"],
            snapshot=None,
            candidates=candidates,
            budget=20,
        )

        self.assertEqual(len(plan["selected"]), 20)
        self.assertEqual(
            _sources(plan),
            {
                "resume_project": 11,
                "history_weakness": 3,
                "domain_knowledge": 2,
                "algorithm_scenario": 4,
            },
        )
        self.assertEqual(plan["rejected"], [])

    def test_full_mock_without_resume_uses_35_45_20(self) -> None:
        candidates: list[dict[str, object]] = []
        number = 0
        for source, count in (
            ("history_weakness", 7),
            ("domain_knowledge", 9),
            ("algorithm_scenario", 4),
        ):
            for _ in range(count):
                number += 1
                candidates.append(_candidate(number, source=source))

        plan = build_question_plan(
            mode="full_mock",
            resume_claims=[],
            snapshot=None,
            candidates=candidates,
            budget=20,
        )

        self.assertEqual(
            _sources(plan),
            {"history_weakness": 7, "domain_knowledge": 9, "algorithm_scenario": 4},
        )
        # No confirmed resume claim: the caller must not pretend to be
        # resume-tailored and the resume bucket is not used.
        self.assertIn("non_resume_tailored", _warning_codes(plan))

    def test_full_mock_never_exceeds_forty_percent_weakness(self) -> None:
        candidates = [_weakness(number) for number in range(1, 8)]
        candidates += [
            _candidate(101, source="domain_knowledge"),
            _candidate(102, source="domain_knowledge"),
            _candidate(103, source="algorithm_scenario"),
        ]

        plan = build_question_plan(
            mode="full_mock",
            resume_claims=[],
            snapshot=None,
            candidates=candidates,
            budget=7,
        )

        selected_weakness = [item for item in plan["selected"] if item.get("weaknessId")]
        # floor(7 * 0.4) == 2; the 40% ceiling stays absolute.
        self.assertEqual(len(selected_weakness), 2)
        self.assertLessEqual(len(selected_weakness), int(7 * 0.4))
        self.assertIn("weakness_ceiling_applied", _warning_codes(plan))

    def test_full_mock_cannot_select_resume_questions_without_confirmed_claims(self) -> None:
        candidates = [
            _candidate(1, source="resume_project", resumeClaimId="R-1"),
            _candidate(2, source="domain_knowledge"),
        ]

        plan = build_question_plan(
            mode="full_mock",
            resume_claims=[],
            snapshot=None,
            candidates=candidates,
            budget=2,
        )

        self.assertEqual([item["source"] for item in plan["selected"]], ["domain_knowledge"])
        self.assertIn("no_confirmed_resume_claim", _rejection_reasons(plan))
        self.assertIn("non_resume_tailored", _warning_codes(plan))

    def test_unconfirmed_resume_claims_do_not_count_as_resume(self) -> None:
        plan = build_question_plan(
            mode="full_mock",
            resume_claims=[{"claimId": "R-1", "confirmed": False}],
            snapshot=None,
            candidates=[_candidate(1, source="resume_project")],
            budget=1,
        )

        self.assertEqual(plan["selected"], [])
        self.assertIn("no_confirmed_resume_claim", _rejection_reasons(plan))

    def test_unknown_resume_claim_id_is_rejected(self) -> None:
        candidates = [
            _candidate(1, source="resume_project", resumeClaimId="R-unknown"),
            _candidate(2, source="resume_project", resumeClaimId="R-1"),
        ]

        plan = build_question_plan(
            mode="full_mock",
            resume_claims=[{"claimId": "R-1", "confirmed": True}],
            snapshot=None,
            candidates=candidates,
            budget=2,
        )

        selected_ids = [item["candidateId"] for item in plan["selected"]]
        self.assertIn("C-002", selected_ids)
        self.assertNotIn("C-001", selected_ids)
        self.assertIn("unknown_resume_claim", _rejection_reasons(plan))


class ProjectTargetedCompositionTests(unittest.TestCase):
    def test_targeted_mode_uses_all_project_weaknesses_without_changing_full_mock(self) -> None:
        weaknesses = [_weakness(number, project_id=PROJECT_A) for number in range(1, 5)]

        targeted = build_question_plan(
            mode="project_targeted",
            project_id=PROJECT_A,
            resume_claims=[],
            snapshot={"projectId": PROJECT_A, "weaknesses": ["W-001", "W-002"]},
            candidates=weaknesses,
            budget=4,
        )
        self.assertEqual(len(targeted["selected"]), 4)
        self.assertEqual(
            [item["source"] for item in targeted["selected"]],
            ["history_weakness"] * 4,
        )
        self.assertNotIn("weakness_ceiling", _rejection_reasons(targeted))

        # The full mock keeps its own 40% ceiling for exactly the same cards.
        full_mock = build_question_plan(
            mode="full_mock",
            resume_claims=["R-1"],
            snapshot=None,
            candidates=weaknesses,
            budget=4,
        )
        selected_weakness = [
            item for item in full_mock["selected"] if item.get("weaknessId")
        ]
        self.assertLessEqual(len(selected_weakness), 1)

    def test_targeted_mode_keeps_every_question_on_the_selected_project(self) -> None:
        candidates = [
            _candidate(1, project_id=PROJECT_A),
            _weakness(2, project_id=PROJECT_B),
            _candidate(3, project_id=None),
            _weakness(4, project_id=PROJECT_A),
        ]

        plan = build_question_plan(
            mode="project_targeted",
            project_id=PROJECT_A,
            resume_claims=["R-1"],
            snapshot={"projectId": PROJECT_A},
            candidates=candidates,
            budget=4,
        )

        self.assertEqual(
            [item["projectId"] for item in plan["selected"]],
            [PROJECT_A, PROJECT_A],
        )
        self.assertEqual(
            _rejection_reasons(plan).count("project_mismatch"),
            2,
        )
        # The other project's weakness never appears in the selected plan.
        self.assertTrue(
            all(item["projectId"] == PROJECT_A for item in plan["selected"])
        )

    def test_targeted_mode_allows_one_basic_mechanism_question(self) -> None:
        candidates = [
            _candidate(1, project_id=PROJECT_A, basicMechanism=True),
            _candidate(2, project_id=PROJECT_A, basicMechanism=True),
            _candidate(3, project_id=PROJECT_A),
        ]

        plan = build_question_plan(
            mode="project_targeted",
            project_id=PROJECT_A,
            resume_claims=[],
            snapshot={"projectId": PROJECT_A},
            candidates=candidates,
            budget=3,
        )

        self.assertEqual(len(plan["selected"]), 2)
        self.assertEqual(
            [item["candidateId"] for item in plan["selected"]],
            ["C-001", "C-003"],
        )
        self.assertIn("basic_mechanism_limit", _rejection_reasons(plan))

    def test_targeted_mode_does_not_apply_full_mock_ratio_quotas(self) -> None:
        candidates = [_weakness(number, project_id=PROJECT_A) for number in range(1, 7)]

        plan = build_question_plan(
            mode="project_targeted",
            project_id=PROJECT_A,
            resume_claims=[],
            snapshot={"projectId": PROJECT_A},
            candidates=candidates,
            budget=6,
        )

        self.assertEqual(len(plan["selected"]), 6)
        self.assertEqual(_sources(plan), {"history_weakness": 6})

    def test_snapshot_from_another_project_is_not_used(self) -> None:
        plan = build_question_plan(
            mode="project_targeted",
            project_id=PROJECT_A,
            resume_claims=[],
            snapshot={"projectId": PROJECT_B, "weaknesses": ["W-B1"]},
            candidates=[_candidate(1, project_id=PROJECT_A)],
            budget=1,
        )

        self.assertEqual(len(plan["selected"]), 1)
        self.assertIn("snapshot_project_mismatch", _warning_codes(plan))


class SharedCardDisciplineTests(unittest.TestCase):
    def test_reposted_source_counts_once_per_origin_group(self) -> None:
        candidates = [
            _candidate(1, project_id=PROJECT_A, originGroupId="G-1"),
            _candidate(2, project_id=PROJECT_A, originGroupId="G-1"),
        ]

        plan = build_question_plan(
            mode="project_targeted",
            project_id=PROJECT_A,
            resume_claims=[],
            snapshot={"projectId": PROJECT_A},
            candidates=candidates,
            budget=2,
        )

        self.assertEqual(len(plan["selected"]), 1)
        self.assertIn("duplicate_origin_group", _rejection_reasons(plan))

    def test_same_question_and_variant_is_rejected_but_a_new_variant_is_allowed(self) -> None:
        candidates = [
            _candidate(1, project_id=PROJECT_A, questionKey="cache", variantId="v1"),
            _candidate(2, project_id=PROJECT_A, questionKey="cache", variantId="v1"),
            _candidate(3, project_id=PROJECT_A, questionKey="cache", variantId="v2"),
        ]

        plan = build_question_plan(
            mode="project_targeted",
            project_id=PROJECT_A,
            resume_claims=[],
            snapshot={"projectId": PROJECT_A},
            candidates=candidates,
            budget=3,
        )

        self.assertEqual(
            [item["candidateId"] for item in plan["selected"]],
            ["C-001", "C-003"],
        )
        self.assertIn("duplicate_question", _rejection_reasons(plan))

    def test_selection_is_bounded_by_the_budget(self) -> None:
        candidates = [_candidate(number, project_id=PROJECT_A) for number in range(1, 6)]

        plan = build_question_plan(
            mode="project_targeted",
            project_id=PROJECT_A,
            resume_claims=[],
            snapshot={"projectId": PROJECT_A},
            candidates=candidates,
            budget=2,
        )

        self.assertEqual(len(plan["selected"]), 2)
        self.assertEqual(len(plan["rejected"]), 3)
        self.assertIn("budget_exhausted", _rejection_reasons(plan))

    def test_planning_does_not_mutate_caller_input(self) -> None:
        candidates = [_candidate(1, project_id=PROJECT_A)]
        frozen = copy.deepcopy(candidates)

        build_question_plan(
            mode="project_targeted",
            project_id=PROJECT_A,
            resume_claims=[],
            snapshot={"projectId": PROJECT_A},
            candidates=candidates,
            budget=1,
        )

        self.assertEqual(candidates, frozen)

    def test_mapping_and_keyword_request_forms_are_equivalent(self) -> None:
        spec = {
            "mode": "project_targeted",
            "project_id": PROJECT_A,
            "resume_claims": [],
            "snapshot": {"projectId": PROJECT_A},
            "candidates": [_candidate(1, project_id=PROJECT_A)],
            "budget": 1,
        }

        from_mapping = build_question_plan(spec)
        from_keywords = build_question_plan(**spec)

        self.assertEqual(set(from_mapping), {"selected", "rejected", "warnings"})
        self.assertEqual(from_mapping, from_keywords)

    def test_invalid_mode_or_budget_is_rejected(self) -> None:
        with self.assertRaises(QuestionPlanError):
            build_question_plan(mode="other", candidates=[], budget=1)
        with self.assertRaises(QuestionPlanError):
            build_question_plan(mode="full_mock", candidates=[], budget=0)
        with self.assertRaises(QuestionPlanError):
            build_question_plan(
                mode="project_targeted", candidates=[], budget=1
            )

    def test_invalid_level_is_rejected(self) -> None:
        plan = build_question_plan(
            mode="project_targeted",
            project_id=PROJECT_A,
            resume_claims=[],
            snapshot={"projectId": PROJECT_A},
            candidates=[_candidate(1, project_id=PROJECT_A, level="L5")],
            budget=1,
        )

        self.assertEqual(plan["selected"], [])
        self.assertIn("invalid_level", _rejection_reasons(plan))


if __name__ == "__main__":
    unittest.main()

class ProjectAliasEntryTests(unittest.TestCase):
    """The readable alias may only select the UUID the learning Skill confirmed."""

    BINDING = {
        "projectAlias": "project-12306",
        "projectId": PROJECT_A,
        "displayName": "12306",
    }

    def test_alias_syntax_is_exact_and_bounded(self) -> None:
        self.assertEqual(validate_project_alias("project-12306"), "project-12306")
        # 56-character suffix is the documented upper bound, still valid.
        self.assertEqual(validate_project_alias("project-" + "a" * 56), "project-" + "a" * 56)
        for bad in (
            "project-12306\n", " project-12306", "project-12306 ", "Project-12306",
            "project-12306/", "project-../12306", "project-12306%2f", "project-",
            "project-" + "a" * 57, "projects-12306",
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(QuestionPlanError):
                    validate_project_alias(bad)

    def test_binding_resolves_the_stable_uuid(self) -> None:
        resolved = resolve_target_project(self.BINDING, "project-12306")
        self.assertEqual(resolved["projectId"], PROJECT_A)
        with self.assertRaises(QuestionPlanError):
            resolve_target_project(self.BINDING, "project-pig-rpc")
        with self.assertRaises(QuestionPlanError):
            resolve_target_project(None, "project-12306")

    def test_targeted_plan_accepts_a_matching_alias_binding(self) -> None:
        plan = build_question_plan(
            mode="project_targeted",
            project_alias="project-12306",
            binding=self.BINDING,
            candidates=[_candidate(1, source="project", project_id=PROJECT_A)],
            budget=3,
        )
        self.assertEqual(len(plan["selected"]), 1)

    def test_alias_binding_can_never_cross_projects(self) -> None:
        with self.assertRaises(QuestionPlanError):
            build_question_plan(
                mode="project_targeted",
                project_id=PROJECT_B,
                project_alias="project-12306",
                binding=self.BINDING,
                candidates=[_candidate(1, source="project", project_id=PROJECT_B)],
                budget=3,
            )

    def test_an_alias_is_rejected_outside_the_targeted_mode(self) -> None:
        with self.assertRaises(QuestionPlanError):
            build_question_plan(
                mode="full_mock",
                project_alias="project-12306",
                binding=self.BINDING,
                candidates=[_candidate(1, source="project", project_id=PROJECT_A)],
                budget=3,
            )
