#!/usr/bin/env python3
"""Pure planning arithmetic for adaptive-study-planning.

This module performs budget arithmetic, used/remaining separation and change
scoping only. It has no network, storage, identity or profile access. It never
infers that the user asked for a downgrade: the caller must already have parsed
an explicit user instruction into ``operation``.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date

OPERATIONS = (
    "initialize",
    "halve_remaining",
    "set_day_budget",
    "set_future_goal",
    "stop_day",
)

WRAP_UP_KEY = "wrap-up"
ROUNDING_QUANTUM = 5
MAX_MINUTES_PER_DAY = 24 * 60
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str) or DATE_PATTERN.match(value) is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _clarification(missing_fields: list[str], reason: str) -> dict:
    return {
        "status": "needs_clarification",
        "missing_fields": missing_fields,
        "reason": reason,
    }


def _invalid(reason: str) -> dict:
    return {"status": "invalid_input", "reason": reason}


def _distribute_proportionally(total: int, tasks: list[dict]) -> list[dict]:
    """Distribute ``total`` minutes across tasks in five-minute units.

    The largest-remainder method keeps the sum exact; ties keep the original
    task order. A final remainder below five minutes becomes a separate wrap-up
    window instead of inflating a learning task.
    """

    if total == 0:
        return []
    if total < ROUNDING_QUANTUM:
        return [{"task_key": WRAP_UP_KEY, "window_minutes": total}]

    weights = [task["window_minutes"] for task in tasks]
    total_weight = sum(weights)
    if total_weight == 0:
        weights = [1 for _ in tasks]
        total_weight = len(tasks)

    units = total // ROUNDING_QUANTUM
    leftover_minutes = total % ROUNDING_QUANTUM

    floors: list[int] = []
    remainders: list[int] = []
    for weight in weights:
        numerator = units * weight
        floors.append(numerator // total_weight)
        remainders.append(numerator % total_weight)

    remaining_units = units - sum(floors)
    order = sorted(range(len(tasks)), key=lambda index: (-remainders[index], index))
    for index in order[:remaining_units]:
        floors[index] += 1

    allocated = [
        {
            "task_key": task["task_key"],
            "window_minutes": floors[index] * ROUNDING_QUANTUM,
        }
        for index, task in enumerate(tasks)
    ]
    if leftover_minutes:
        allocated.append(
            {"task_key": WRAP_UP_KEY, "window_minutes": leftover_minutes}
        )
    return allocated


def _allocate_remaining(
    total: int,
    tasks: list[dict],
    priority_keys: tuple[str, ...] = (),
) -> list[dict]:
    """Allocate ``total`` minutes, satisfying named priority tasks first.

    Priority tasks keep their full window when the budget can cover them. The
    caller rejects the request when it cannot. The remaining budget is then
    distributed across the other tasks; if nothing is left for them, a wrap-up
    window carries any sub-five-minute remainder.
    """

    if total == 0:
        return []
    if total < ROUNDING_QUANTUM:
        return [{"task_key": WRAP_UP_KEY, "window_minutes": total}]
    if not priority_keys:
        return _distribute_proportionally(total, tasks)

    priority_tasks = [task for task in tasks if task["task_key"] in priority_keys]
    other_tasks = [task for task in tasks if task["task_key"] not in priority_keys]
    pinned_total = sum(task["window_minutes"] for task in priority_tasks)
    rest_total = total - pinned_total

    if rest_total > 0 and not other_tasks:
        distributed = [{"task_key": WRAP_UP_KEY, "window_minutes": rest_total}]
    elif rest_total > 0:
        distributed = _distribute_proportionally(rest_total, other_tasks)
    else:
        distributed = []

    by_key = {item["task_key"]: item["window_minutes"] for item in distributed}
    allocated: list[dict] = []
    for task in tasks:
        key = task["task_key"]
        if key in priority_keys:
            allocated.append(
                {"task_key": key, "window_minutes": task["window_minutes"]}
            )
        else:
            allocated.append({"task_key": key, "window_minutes": by_key.get(key, 0)})
    for item in distributed:
        if item["task_key"] == WRAP_UP_KEY:
            allocated.append(item)
    return allocated


def _pinned_minutes(tasks: list[dict], priority_keys: tuple[str, ...]) -> int:
    return sum(
        task["window_minutes"] for task in tasks if task["task_key"] in priority_keys
    )


def _validate_tasks(value: object) -> tuple[list[dict] | None, str | None]:
    if not isinstance(value, list):
        return None, "remaining_tasks must be an array"
    tasks: list[dict] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            return None, f"remaining_tasks[{index}] must be an object"
        key = item.get("task_key")
        if not isinstance(key, str) or not key.strip():
            return None, f"remaining_tasks[{index}].task_key must be a non-empty string"
        key = key.strip()
        if key == WRAP_UP_KEY:
            return None, f"task_key {WRAP_UP_KEY!r} is reserved for the closing window"
        if key in seen:
            return None, f"duplicate task_key {key!r}"
        seen.add(key)
        minutes = item.get("window_minutes")
        if not _is_int(minutes) or not 0 <= minutes <= MAX_MINUTES_PER_DAY:
            return None, (
                f"remaining_tasks[{index}].window_minutes must be an integer "
                f"between 0 and {MAX_MINUTES_PER_DAY}"
            )
        tasks.append({"task_key": key, "window_minutes": minutes})
    return tasks, None


def _validate_minutes(
    request: dict,
    field: str,
    *,
    required: bool,
    missing: list[str],
) -> tuple[int | None, str | None]:
    if field not in request or request.get(field) is None:
        if required:
            missing.append(field)
        return None, None
    value = request.get(field)
    if not _is_int(value) or not 0 <= value <= MAX_MINUTES_PER_DAY:
        return None, f"{field} must be an integer between 0 and {MAX_MINUTES_PER_DAY}"
    return value, None


def _result(
    request: dict,
    *,
    operation: str,
    business_date: str,
    goal: int,
    effective_day: int,
    used: int,
    tasks: list[dict],
    change_scope: str,
    reason: str,
    future_goal: dict | None = None,
    cancelled_tasks: list[str] | None = None,
) -> dict:
    remaining = sum(task["window_minutes"] for task in tasks)
    result = {
        "status": "applied",
        "operation": operation,
        "business_date": business_date,
        "goal_daily_minutes": goal,
        "effective_day_minutes": effective_day,
        "reported_used_window_minutes": used,
        "budgeted_remaining_minutes": remaining,
        "remaining_tasks": tasks,
        "change_scope": change_scope,
        "overrun_minutes": max(0, used - effective_day),
        "reason": reason,
    }
    if future_goal is not None:
        result["future_goal"] = future_goal
    if cancelled_tasks is not None:
        result["cancelled_tasks"] = cancelled_tasks
    return result


def evaluate_plan(request: dict) -> dict:
    """Evaluate one normalized planning request and return a JSON-ready dict.

    Status is ``applied``, ``needs_clarification`` or ``invalid_input``. A
    clarification or invalid result never contains a fabricated plan.
    """

    if not isinstance(request, dict):
        return _invalid("request must be a JSON object")

    operation = request.get("operation")
    if operation is None or operation == "":
        return _clarification(["operation"], "operation is required")
    if operation not in OPERATIONS:
        return _invalid(f"unknown operation {operation!r}")

    business_date_raw = request.get("business_date")
    if business_date_raw is None:
        return _clarification(["business_date"], "business_date is required")
    business_date_value = _parse_date(business_date_raw)
    if business_date_value is None:
        return _invalid("business_date must be a valid date in YYYY-MM-DD form")

    missing: list[str] = []

    goal, error = _validate_minutes(
        request, "goal_daily_minutes", required=True, missing=missing
    )
    if error:
        return _invalid(error)

    effective_day, error = _validate_minutes(
        request,
        "effective_day_minutes",
        required=operation != "initialize",
        missing=missing,
    )
    if error:
        return _invalid(error)

    used, error = _validate_minutes(
        request,
        "reported_used_window_minutes",
        required=True,
        missing=missing,
    )
    if error:
        return _invalid(error)

    tasks_value = request.get("remaining_tasks")
    tasks: list[dict] | None = None
    if tasks_value is None:
        missing.append("remaining_tasks")
    else:
        tasks, error = _validate_tasks(tasks_value)
        if error:
            return _invalid(error)

    new_budget: int | None = None
    if operation in ("set_day_budget", "set_future_goal"):
        new_budget, error = _validate_minutes(
            request, "new_budget_minutes", required=True, missing=missing
        )
        if error:
            return _invalid(error)

    effective_from: str | None = None
    if operation == "set_future_goal":
        raw_effective_from = request.get("effective_from")
        if raw_effective_from is None:
            missing.append("effective_from")
        else:
            parsed = _parse_date(raw_effective_from)
            if parsed is None:
                return _invalid(
                    "effective_from must be a valid date in YYYY-MM-DD form"
                )
            effective_from = raw_effective_from

    if missing:
        return _clarification(
            missing,
            "missing required planning fields: " + ", ".join(missing),
        )

    assert goal is not None
    assert used is not None
    assert tasks is not None

    priority_keys: tuple[str, ...] = ()
    raw_priority = request.get("priority_task_keys")
    if raw_priority is not None:
        if not isinstance(raw_priority, list):
            return _invalid("priority_task_keys must be an array of task keys")
        normalized: list[str] = []
        for item in raw_priority:
            if not isinstance(item, str) or not item.strip():
                return _invalid(
                    "priority_task_keys entries must be non-empty task keys"
                )
            normalized.append(item.strip())
        if len(set(normalized)) != len(normalized):
            return _invalid("priority_task_keys must not contain duplicates")
        known = {task["task_key"] for task in tasks}
        unknown = [key for key in normalized if key not in known]
        if unknown:
            return _invalid(
                "priority_task_keys reference unknown tasks: "
                + ", ".join(sorted(unknown))
            )
        priority_keys = tuple(normalized)

    if operation == "initialize":
        if effective_day is None:
            effective_day = goal
        if used != 0:
            return _invalid(
                "initialize requires reported_used_window_minutes 0; "
                "use another operation after the day starts"
            )
    assert effective_day is not None

    task_total = sum(task["window_minutes"] for task in tasks)
    if used + task_total != effective_day:
        return _invalid(
            f"reported_used_window_minutes {used} + remaining task minutes "
            f"{task_total} = {used + task_total} does not equal "
            f"effective_day_minutes {effective_day}; confirm the facts first"
        )

    if operation == "initialize":
        if effective_day > 0 and not tasks:
            return _invalid("initialize needs at least one remaining task")
        return _result(
            request,
            operation=operation,
            business_date=str(business_date_raw),
            goal=goal,
            effective_day=effective_day,
            used=used,
            tasks=tasks,
            change_scope="none",
            reason=(
                f"initialized {effective_day} planned minutes with {used} "
                f"reported-used minutes; long-term goal {goal}"
            ),
        )

    if operation == "halve_remaining":
        halved_total = task_total // 2
        if halved_total > 0 and not tasks:
            return _invalid("cannot halve an empty remaining plan")
        if _pinned_minutes(tasks, priority_keys) > halved_total:
            return _invalid(
                "priority tasks need more minutes than the halved remaining budget"
            )
        allocated = _allocate_remaining(halved_total, tasks, priority_keys)
        return _result(
            request,
            operation=operation,
            business_date=str(business_date_raw),
            goal=goal,
            effective_day=used + halved_total,
            used=used,
            tasks=allocated,
            change_scope="day",
            reason=(
                f"remaining {task_total} min halved to {halved_total} min; "
                f"used {used} min and the {goal} min long-term goal unchanged"
            ),
        )

    if operation == "set_day_budget":
        assert new_budget is not None
        remaining_budget = max(0, new_budget - used)
        if remaining_budget > 0 and not tasks:
            return _invalid(
                "cannot distribute a positive remaining budget across no tasks"
            )
        if _pinned_minutes(tasks, priority_keys) > remaining_budget:
            return _invalid(
                "priority tasks need more minutes than the remaining day budget"
            )
        allocated = _allocate_remaining(remaining_budget, tasks, priority_keys)
        overrun = max(0, used - new_budget)
        extra = (
            f"; reported use exceeds the new day budget by {overrun} min"
            if overrun
            else ""
        )
        return _result(
            request,
            operation=operation,
            business_date=str(business_date_raw),
            goal=goal,
            effective_day=new_budget,
            used=used,
            tasks=allocated,
            change_scope="day",
            reason=(
                f"day budget set to {new_budget} min with {used} min used; "
                f"long-term goal stays {goal} min{extra}"
            ),
        )

    if operation == "set_future_goal":
        assert new_budget is not None
        assert effective_from is not None
        effective_from_value = _parse_date(effective_from)
        assert effective_from_value is not None
        if effective_from_value < business_date_value:
            return _invalid(
                "effective_from cannot be earlier than business_date"
            )

        if effective_from_value > business_date_value:
            return _result(
                request,
                operation=operation,
                business_date=str(business_date_raw),
                goal=goal,
                effective_day=effective_day,
                used=used,
                tasks=tasks,
                change_scope="future_goal",
                future_goal={
                    "minutes": new_budget,
                    "effective_from": effective_from,
                },
                reason=(
                    f"future daily goal set to {new_budget} min from "
                    f"{effective_from}; today remains {effective_day} min "
                    f"against the {goal} min goal"
                ),
            )

        remaining_budget = max(0, new_budget - used)
        if remaining_budget > 0 and not tasks:
            return _invalid(
                "cannot distribute a positive remaining budget across no tasks"
            )
        if _pinned_minutes(tasks, priority_keys) > remaining_budget:
            return _invalid(
                "priority tasks need more minutes than the remaining day budget"
            )
        allocated = _allocate_remaining(remaining_budget, tasks, priority_keys)
        overrun = max(0, used - new_budget)
        extra = (
            f"; reported use exceeds the new day budget by {overrun} min"
            if overrun
            else ""
        )
        return _result(
            request,
            operation=operation,
            business_date=str(business_date_raw),
            goal=new_budget,
            effective_day=new_budget,
            used=used,
            tasks=allocated,
            change_scope="future_goal",
            future_goal={
                "minutes": new_budget,
                "effective_from": effective_from,
            },
            reason=(
                f"daily goal changed to {new_budget} min effective today; "
                f"reported use {used} min{extra}"
            ),
        )

    if operation == "stop_day":
        cancelled = [
            task["task_key"] for task in tasks if task["window_minutes"] > 0
        ]
        return _result(
            request,
            operation=operation,
            business_date=str(business_date_raw),
            goal=goal,
            effective_day=effective_day,
            used=used,
            tasks=[],
            change_scope="day",
            cancelled_tasks=cancelled,
            reason=(
                f"day stopped; {len(cancelled)} remaining tasks cancelled, "
                f"not completed; goal {goal} min unchanged"
            ),
        )

    return _invalid(f"operation {operation!r} is not implemented")


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        print("expected one JSON object on standard input", file=sys.stderr)
        return 2
    try:
        request = json.loads(raw)
    except json.JSONDecodeError as error:
        print(f"invalid JSON input: {error.msg}", file=sys.stderr)
        return 2
    print(json.dumps(evaluate_plan(request), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
