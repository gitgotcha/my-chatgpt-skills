"""Deterministic tests for the pure planning rules.

These tests cover the arithmetic only. They do not claim that a model follows
the prose workflow, and they never write profile data.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "planning_rules.py"


def _load_planning_module():
    spec = importlib.util.spec_from_file_location("planning_rules", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


planning = _load_planning_module()


def make_tasks(*pairs):
    return [
        {"task_key": key, "window_minutes": minutes}
        for key, minutes in pairs
    ]


def request(operation, **overrides):
    payload = {
        "operation": operation,
        "business_date": "2026-10-20",
        "goal_daily_minutes": 600,
        "effective_day_minutes": 600,
        "reported_used_window_minutes": 0,
        "remaining_tasks": make_tasks(
            ("12306", 120),
            ("RPC", 120),
            ("Vibe Coding", 60),
            ("Agent knowledge", 60),
            ("Resume basics", 60),
            ("Interview review", 60),
            ("Algorithm", 90),
            ("Skill work", 30),
        ),
    }
    payload.update(overrides)
    return payload


def task_map(result):
    return {
        item["task_key"]: item["window_minutes"]
        for item in result["remaining_tasks"]
    }


class InitializeTests(unittest.TestCase):
    def test_initializes_the_confirmed_ten_hour_groups(self):
        grouped = request(
            "initialize",
            remaining_tasks=make_tasks(
                ("morning-project", 240),
                ("afternoon-knowledge", 180),
                ("interview-review", 60),
                ("evening-algorithm-skill", 120),
            ),
        )
        result = planning.evaluate_plan(grouped)

        self.assertEqual("applied", result["status"])
        self.assertEqual(600, result["goal_daily_minutes"])
        self.assertEqual(600, result["effective_day_minutes"])
        self.assertEqual(0, result["reported_used_window_minutes"])
        self.assertEqual(600, result["budgeted_remaining_minutes"])
        self.assertEqual("none", result["change_scope"])
        self.assertEqual(600, sum(task_map(result).values()))

    def test_unknown_used_window_requests_clarification(self):
        result = planning.evaluate_plan(
            request("initialize", reported_used_window_minutes=None)
        )

        self.assertEqual("needs_clarification", result["status"])
        self.assertIn("reported_used_window_minutes", result["missing_fields"])
        self.assertNotIn("budgeted_remaining_minutes", result)

    def test_initialize_rejects_an_already_started_day(self):
        result = planning.evaluate_plan(
            request(
                "initialize",
                reported_used_window_minutes=60,
                remaining_tasks=make_tasks(("12306", 540)),
            )
        )

        self.assertEqual("invalid_input", result["status"])
        self.assertIn("initialize", result["reason"])

    def test_initialize_rejects_inconsistent_task_total(self):
        result = planning.evaluate_plan(
            request(
                "initialize",
                remaining_tasks=make_tasks(("12306", 120)),
            )
        )

        self.assertEqual("invalid_input", result["status"])
        self.assertNotIn("budgeted_remaining_minutes", result)


class HalveRemainingTests(unittest.TestCase):
    def test_acceptance_round_three_halves_only_the_remaining_budget(self):
        result = planning.evaluate_plan(
            request(
                "halve_remaining",
                effective_day_minutes=600,
                reported_used_window_minutes=360,
                remaining_tasks=make_tasks(
                    ("Resume basics", 60),
                    ("Interview review", 60),
                    ("Algorithm", 90),
                    ("Skill work", 30),
                ),
            )
        )

        self.assertEqual("applied", result["status"])
        self.assertEqual(480, result["effective_day_minutes"])
        self.assertEqual(600, result["goal_daily_minutes"])
        self.assertEqual(360, result["reported_used_window_minutes"])
        self.assertEqual(120, result["budgeted_remaining_minutes"])
        self.assertEqual(
            {
                "Resume basics": 30,
                "Interview review": 30,
                "Algorithm": 45,
                "Skill work": 15,
            },
            task_map(result),
        )
        self.assertEqual("day", result["change_scope"])

    def test_odd_total_is_floored_before_allocation(self):
        result = planning.evaluate_plan(
            request(
                "halve_remaining",
                effective_day_minutes=19,
                reported_used_window_minutes=10,
                remaining_tasks=make_tasks(("a", 3), ("b", 3), ("c", 3)),
            )
        )

        self.assertEqual("applied", result["status"])
        self.assertEqual(14, result["effective_day_minutes"])
        self.assertEqual(4, result["budgeted_remaining_minutes"])
        remaining = task_map(result)
        self.assertEqual(4, sum(remaining.values()))
        self.assertIn("wrap-up", remaining)
        self.assertTrue(all(minutes >= 0 for minutes in remaining.values()))

    def test_unknown_used_window_is_not_filled_with_zero(self):
        result = planning.evaluate_plan(
            request("halve_remaining", reported_used_window_minutes=None)
        )

        self.assertEqual("needs_clarification", result["status"])
        self.assertIn("reported_used_window_minutes", result["missing_fields"])

    def test_inconsistent_used_and_remaining_is_rejected(self):
        result = planning.evaluate_plan(
            request(
                "halve_remaining",
                effective_day_minutes=600,
                reported_used_window_minutes=300,
                remaining_tasks=make_tasks(
                    ("Resume basics", 60),
                    ("Interview review", 60),
                    ("Algorithm", 90),
                    ("Skill work", 30),
                ),
            )
        )

        self.assertEqual("invalid_input", result["status"])
        self.assertIn("540", result["reason"])


class DayBudgetTests(unittest.TestCase):
    def test_used_time_beyond_the_new_budget_never_goes_negative(self):
        result = planning.evaluate_plan(
            request(
                "set_day_budget",
                new_budget_minutes=300,
                effective_day_minutes=600,
                reported_used_window_minutes=360,
                remaining_tasks=make_tasks(
                    ("Resume basics", 60),
                    ("Interview review", 60),
                    ("Algorithm", 90),
                    ("Skill work", 30),
                ),
            )
        )

        self.assertEqual("applied", result["status"])
        self.assertEqual(360, result["reported_used_window_minutes"])
        self.assertEqual(300, result["effective_day_minutes"])
        self.assertEqual(0, result["budgeted_remaining_minutes"])
        self.assertEqual([], result["remaining_tasks"])
        self.assertEqual(60, result["overrun_minutes"])
        self.assertEqual(600, result["goal_daily_minutes"])

    def test_reallocates_exactly_and_keeps_five_minute_units(self):
        result = planning.evaluate_plan(
            request(
                "set_day_budget",
                new_budget_minutes=480,
                effective_day_minutes=600,
                reported_used_window_minutes=360,
                remaining_tasks=make_tasks(
                    ("Resume basics", 60),
                    ("Interview review", 60),
                    ("Algorithm", 90),
                    ("Skill work", 30),
                ),
            )
        )

        self.assertEqual("applied", result["status"])
        self.assertEqual(120, result["budgeted_remaining_minutes"])
        self.assertTrue(
            all(minutes % 5 == 0 for minutes in task_map(result).values())
        )

    def test_largest_remainder_ties_follow_original_order(self):
        result = planning.evaluate_plan(
            request(
                "set_day_budget",
                new_budget_minutes=20,
                effective_day_minutes=30,
                reported_used_window_minutes=0,
                remaining_tasks=make_tasks(("first", 10), ("second", 10), ("third", 10)),
            )
        )

        self.assertEqual("applied", result["status"])
        self.assertEqual(
            {"first": 10, "second": 5, "third": 5},
            task_map(result),
        )
        self.assertEqual(20, sum(task_map(result).values()))

    def test_leftover_under_five_minutes_becomes_a_wrap_up_window(self):
        result = planning.evaluate_plan(
            request(
                "set_day_budget",
                new_budget_minutes=122,
                effective_day_minutes=120,
                reported_used_window_minutes=0,
                remaining_tasks=make_tasks(("first", 60), ("second", 60)),
            )
        )

        self.assertEqual("applied", result["status"])
        self.assertEqual(122, result["budgeted_remaining_minutes"])
        remaining = task_map(result)
        self.assertEqual(2, remaining["wrap-up"])
        self.assertEqual(122, sum(remaining.values()))

    def test_budget_below_five_minutes_is_only_a_wrap_up_window(self):
        result = planning.evaluate_plan(
            request(
                "set_day_budget",
                new_budget_minutes=3,
                effective_day_minutes=30,
                reported_used_window_minutes=0,
                remaining_tasks=make_tasks(("first", 15), ("second", 15)),
            )
        )

        self.assertEqual("applied", result["status"])
        self.assertEqual(
            [{"task_key": "wrap-up", "window_minutes": 3}],
            result["remaining_tasks"],
        )

    def test_budget_below_five_minutes_does_not_create_a_priority_task(self):
        result = planning.evaluate_plan(
            request(
                "set_day_budget",
                new_budget_minutes=3,
                effective_day_minutes=30,
                reported_used_window_minutes=0,
                remaining_tasks=make_tasks(("pinned", 0), ("second", 30)),
                priority_task_keys=["pinned"],
            )
        )

        self.assertEqual("applied", result["status"])
        self.assertEqual(
            [{"task_key": "wrap-up", "window_minutes": 3}],
            result["remaining_tasks"],
        )

    def test_day_budget_does_not_change_the_long_term_goal(self):
        result = planning.evaluate_plan(
            request(
                "set_day_budget",
                new_budget_minutes=300,
                effective_day_minutes=600,
                reported_used_window_minutes=0,
            )
        )

        self.assertEqual(600, result["goal_daily_minutes"])
        self.assertEqual(300, result["effective_day_minutes"])

    def test_priority_task_is_satisfied_before_the_others(self):
        result = planning.evaluate_plan(
            request(
                "set_day_budget",
                new_budget_minutes=120,
                effective_day_minutes=240,
                reported_used_window_minutes=0,
                remaining_tasks=make_tasks(
                    ("priority", 60),
                    ("second", 60),
                    ("third", 90),
                    ("fourth", 30),
                ),
                priority_task_keys=["priority"],
            )
        )

        self.assertEqual("applied", result["status"])
        self.assertEqual(60, task_map(result)["priority"])
        self.assertEqual(120, sum(task_map(result).values()))

    def test_priority_tasks_that_exceed_the_budget_are_rejected(self):
        result = planning.evaluate_plan(
            request(
                "set_day_budget",
                new_budget_minutes=30,
                effective_day_minutes=120,
                reported_used_window_minutes=0,
                remaining_tasks=make_tasks(("priority", 60), ("second", 60)),
                priority_task_keys=["priority"],
            )
        )

        self.assertEqual("invalid_input", result["status"])
        self.assertIn("priority", result["reason"])


class FutureGoalTests(unittest.TestCase):
    def test_future_goal_starts_next_day_and_leaves_today_alone(self):
        result = planning.evaluate_plan(
            request(
                "set_future_goal",
                new_budget_minutes=480,
                effective_from="2026-10-21",
            )
        )

        self.assertEqual("applied", result["status"])
        self.assertEqual(600, result["goal_daily_minutes"])
        self.assertEqual(600, result["effective_day_minutes"])
        self.assertEqual(600, result["budgeted_remaining_minutes"])
        self.assertEqual("future_goal", result["change_scope"])
        self.assertEqual(
            {"minutes": 480, "effective_from": "2026-10-21"},
            result["future_goal"],
        )

    def test_goal_effective_today_changes_today_and_the_goal(self):
        result = planning.evaluate_plan(
            request(
                "set_future_goal",
                new_budget_minutes=480,
                effective_from="2026-10-20",
            )
        )

        self.assertEqual("applied", result["status"])
        self.assertEqual(480, result["goal_daily_minutes"])
        self.assertEqual(480, result["effective_day_minutes"])
        self.assertEqual(480, result["budgeted_remaining_minutes"])
        self.assertEqual("future_goal", result["change_scope"])
        self.assertEqual("2026-10-20", result["future_goal"]["effective_from"])

    def test_effective_from_before_today_is_rejected(self):
        result = planning.evaluate_plan(
            request(
                "set_future_goal",
                new_budget_minutes=480,
                effective_from="2026-10-19",
            )
        )

        self.assertEqual("invalid_input", result["status"])

    def test_missing_effective_from_requests_clarification(self):
        result = planning.evaluate_plan(
            request("set_future_goal", new_budget_minutes=480)
        )

        self.assertEqual("needs_clarification", result["status"])
        self.assertIn("effective_from", result["missing_fields"])


class StopDayTests(unittest.TestCase):
    def test_stop_day_cancels_remaining_tasks_without_completing_them(self):
        result = planning.evaluate_plan(
            request(
                "stop_day",
                effective_day_minutes=480,
                reported_used_window_minutes=360,
                remaining_tasks=make_tasks(
                    ("Resume basics", 30),
                    ("Interview review", 30),
                    ("Algorithm", 45),
                    ("Skill work", 15),
                ),
            )
        )

        self.assertEqual("applied", result["status"])
        self.assertEqual(0, result["budgeted_remaining_minutes"])
        self.assertEqual([], result["remaining_tasks"])
        self.assertEqual(
            ["Resume basics", "Interview review", "Algorithm", "Skill work"],
            result["cancelled_tasks"],
        )
        self.assertEqual(600, result["goal_daily_minutes"])
        self.assertEqual(480, result["effective_day_minutes"])


class InputValidationTests(unittest.TestCase):
    def test_duplicate_task_keys_are_rejected(self):
        result = planning.evaluate_plan(
            request(
                "initialize",
                remaining_tasks=make_tasks(("12306", 300), ("12306", 300)),
            )
        )

        self.assertEqual("invalid_input", result["status"])
        self.assertIn("duplicate", result["reason"].lower())

    def test_negative_window_is_rejected(self):
        result = planning.evaluate_plan(
            request(
                "initialize",
                remaining_tasks=make_tasks(("12306", -5), ("RPC", 605)),
            )
        )

        self.assertEqual("invalid_input", result["status"])

    def test_boolean_is_not_accepted_as_minutes(self):
        result = planning.evaluate_plan(
            request(
                "initialize",
                goal_daily_minutes=True,
            )
        )

        self.assertEqual("invalid_input", result["status"])

    def test_missing_goal_requests_clarification(self):
        result = planning.evaluate_plan(request("initialize", goal_daily_minutes=None))

        self.assertEqual("needs_clarification", result["status"])
        self.assertIn("goal_daily_minutes", result["missing_fields"])

    def test_missing_operation_requests_clarification(self):
        result = planning.evaluate_plan({"business_date": "2026-10-20"})

        self.assertEqual("needs_clarification", result["status"])
        self.assertIn("operation", result["missing_fields"])

    def test_unknown_operation_is_invalid(self):
        result = planning.evaluate_plan(request("extend_day"))

        self.assertEqual("invalid_input", result["status"])

    def test_bad_business_date_is_invalid(self):
        result = planning.evaluate_plan(
            request("initialize", business_date="2026/10/20")
        )

        self.assertEqual("invalid_input", result["status"])

    def test_more_than_a_day_of_minutes_is_invalid(self):
        result = planning.evaluate_plan(
            request(
                "initialize",
                goal_daily_minutes=1441,
                effective_day_minutes=1441,
                remaining_tasks=make_tasks(("everything", 1441)),
            )
        )

        self.assertEqual("invalid_input", result["status"])

    def test_empty_remaining_tasks_cannot_absorb_a_positive_budget(self):
        result = planning.evaluate_plan(
            request("initialize", remaining_tasks=[])
        )

        self.assertEqual("invalid_input", result["status"])

    def test_calls_are_pure(self):
        first = planning.evaluate_plan(request("initialize"))
        second = planning.evaluate_plan(request("initialize"))

        self.assertEqual(first, second)
        self.assertEqual(600, sum(task_map(first).values()))


class CommandLineTests(unittest.TestCase):
    def _run(self, payload):
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_standard_input_and_output_carry_one_json_document(self):
        completed = self._run(request("initialize"))

        self.assertEqual(0, completed.returncode, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual("applied", result["status"])
        self.assertEqual(600, result["budgeted_remaining_minutes"])

    def test_malformed_json_fails_without_a_plan(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input="{not json",
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertNotEqual(0, completed.returncode)
        self.assertEqual("", completed.stdout.strip())

    def test_cli_returns_clarification_as_json(self):
        completed = self._run(request("initialize", goal_daily_minutes=None))

        self.assertEqual(0, completed.returncode, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual("needs_clarification", result["status"])


if __name__ == "__main__":
    unittest.main()
