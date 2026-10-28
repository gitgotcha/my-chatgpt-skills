"""Pure question-plan constraints for a mock or project-targeted interview.

The conversational model owns the *semantics* of a question: wording, expected
answer, follow-up branches and evidence.  This module only owns composition:

* ``mode="full_mock"`` keeps the documented exclusive source mix
  (55/15/10/20 with a confirmed resume; 35/45/20 without one) and the absolute
  40% ceiling for weakness retests.  It is the machine-checkable mirror of the
  rules the user already knows, not a new policy.
* ``mode="project_targeted"`` only accepts candidate cards that can be traced
  back to the selected ``project_id``.  It never applies the full-mock ratio or
  the 40% ceiling, and it allows at most one basic-mechanism question.

The function is pure: it never performs network, model, file or cloud I/O and
never mutates the caller's cards.  Candidate cards are supplied by the caller
(see ``references/project-targeted-interview.md`` and
``references/web-question-sourcing.md`` for their fields).
"""

from __future__ import annotations

from copy import deepcopy
from math import floor
import re
from typing import Mapping, Sequence

MODE_FULL_MOCK = "full_mock"
MODE_PROJECT_TARGETED = "project_targeted"
MODES = frozenset({MODE_FULL_MOCK, MODE_PROJECT_TARGETED})

# Exclusive main-source weights from references/interview-protocol.md.  Domain
# knowledge may be combined with a project scenario, but it is counted once by
# its main source (``topicTags`` marks the overlap on the session event).
FULL_MOCK_WITH_RESUME = {
    "resume_project": 55,
    "history_weakness": 15,
    "domain_knowledge": 10,
    "algorithm_scenario": 20,
}
FULL_MOCK_WITHOUT_RESUME = {
    "history_weakness": 35,
    "domain_knowledge": 45,
    "algorithm_scenario": 20,
}
WEAKNESS_CEILING_DIVISOR = 5  # 40% == 2/5, kept integral to avoid float edges
MAX_BASIC_MECHANISM_QUESTIONS = 1
_LEVELS = frozenset({"L1", "L2", "L3", "L4"})
# Project entry aliases are readable selectors, never storage domains.  The
# syntax is shared with software-project-learning's alias contract; this copy is
# intentionally tiny and anchored so a mismatch can never silently pass.
PROJECT_ALIAS_PATTERN = re.compile(r"project-[a-z0-9](?:[a-z0-9-]{0,54}[a-z0-9])?\Z")


def validate_project_alias(value: object) -> str:
    """Return the alias unchanged, or raise for anything but the exact syntax."""
    if not isinstance(value, str):
        raise QuestionPlanError("project alias must be a string")
    if len(value) < 9 or len(value) > 64 or PROJECT_ALIAS_PATTERN.fullmatch(value) is None:
        raise QuestionPlanError("invalid project alias")
    return value


def resolve_target_project(binding: Mapping[str, object] | None, alias: object) -> dict[str, str]:
    """Resolve a confirmed binding + alias to the stable project UUID.

    Pure: it only checks consistency.  The caller must have obtained the binding
    from the learning Skill's full projection read (confirmed, projected and
    visible in active evidence); this helper never invents or re-derives a UUID.
    """
    confirmed = validate_project_alias(alias)
    if not isinstance(binding, Mapping):
        raise QuestionPlanError("project alias requires a confirmed project binding")
    binding_alias = binding.get("projectAlias")
    project_id = binding.get("projectId")
    if binding_alias != confirmed:
        raise QuestionPlanError("binding alias does not match the requested alias")
    if not isinstance(project_id, str) or not project_id.strip():
        raise QuestionPlanError("binding has no stable project id")
    return {
        "projectAlias": confirmed,
        "projectId": project_id.strip(),
        "displayName": str(binding.get("displayName", "")),
    }
_WEAKNESS_TAGS = frozenset(
    {"profileweakness", "profile_weakness", "weakness", "historyweakness"}
)

_SOURCE_ALIASES = {
    "resume": "resume_project",
    "project": "resume_project",
    "project_resume": "resume_project",
    "resume_project": "resume_project",
    "profile_weakness": "history_weakness",
    "weakness": "history_weakness",
    "history_weakness": "history_weakness",
    "domain": "domain_knowledge",
    "domain_knowledge": "domain_knowledge",
    "algorithm": "algorithm_scenario",
    "algorithm_and_scenario": "algorithm_scenario",
    "algorithm_scenario": "algorithm_scenario",
}


class QuestionPlanError(ValueError):
    """Raised when the plan request itself is malformed (not a candidate)."""


def _field(card: Mapping[str, object], *names: str) -> object | None:
    for name in names:
        if name in card:
            return card[name]
    return None


def _claimed_resume_ids(value: object) -> tuple[set[str], list[dict[str, str]]]:
    """Return confirmed resume claim IDs; ignore explicitly unconfirmed ones."""
    warnings: list[dict[str, str]] = []
    if value is None:
        return set(), warnings
    if isinstance(value, str):
        return ({value.strip()} if value.strip() else set()), warnings
    if isinstance(value, Mapping):
        entries: list[object] = [
            {"claimId": key, "confirmed": confirmed}
            for key, confirmed in value.items()
        ]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        entries = list(value)
    else:
        warnings.append({
            "code": "unusable_resume_claim",
            "detail": "resume_claims must be a list of claim IDs or claim objects",
        })
        return set(), warnings

    claims: set[str] = set()
    for entry in entries:
        if isinstance(entry, str):
            claim_id = entry.strip()
            confirmed = True
        elif isinstance(entry, Mapping):
            claim_id_value = _field(entry, "claimId", "claim_id", "id")
            claim_id = claim_id_value.strip() if isinstance(claim_id_value, str) else ""
            confirmed = entry.get("confirmed") is not False
        else:
            claim_id = ""
            confirmed = False
        if not claim_id:
            warnings.append({
                "code": "unusable_resume_claim",
                "detail": f"ignored resume claim without a stable ID: {entry!r}",
            })
            continue
        if not confirmed:
            # An unconfirmed claim is not evidence; never turn it into a resume
            # question or invent the experience behind it.
            continue
        claims.add(claim_id)
    return claims, warnings


def _allocate(total: int, weights: Mapping[str, int]) -> dict[str, int]:
    """Largest-remainder allocation over integer percentages."""
    total_weight = sum(weights.values())
    raw = {name: total * weight / total_weight for name, weight in weights.items()}
    allocated = {name: floor(value) for name, value in raw.items()}
    remaining = total - sum(allocated.values())
    order = sorted(
        weights,
        key=lambda name: (-(raw[name] - allocated[name]), list(weights).index(name)),
    )
    for name in order[:remaining]:
        allocated[name] += 1
    return allocated


def _weakness_card(card: Mapping[str, object], source: str | None) -> bool:
    if source == "history_weakness":
        return True
    if _field(card, "weaknessId", "weakness_id"):
        return True
    tags = _field(card, "sourceTags", "source_tags")
    if isinstance(tags, Sequence) and not isinstance(tags, (str, bytes)):
        return any(
            isinstance(tag, str) and tag.strip().lower() in _WEAKNESS_TAGS
            for tag in tags
        )
    return False


def _read_candidate(
    candidate: object, index: int, mode: str
) -> tuple[dict[str, object] | None, str | None]:
    """Validate one candidate card; return ``(record, rejection_reason)``."""
    if not isinstance(candidate, Mapping):
        return None, "invalid_candidate"

    candidate_id = _field(candidate, "candidateId", "candidate_id", "id")
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        return None, "missing_candidate_id"
    candidate_id = candidate_id.strip()

    source_value = _field(candidate, "source")
    if source_value is None:
        normalized_source: str | None = None
    elif isinstance(source_value, str):
        normalized_source = _SOURCE_ALIASES.get(source_value.strip().lower())
    else:
        return None, "invalid_candidate"
    if mode == MODE_FULL_MOCK and normalized_source is None:
        return None, "unknown_source"

    project_id = _field(candidate, "projectId", "project_id")
    if project_id is not None and not isinstance(project_id, str):
        return None, "invalid_candidate"

    level = _field(candidate, "level")
    if level is not None:
        if not isinstance(level, str) or level.strip().upper() not in _LEVELS:
            return None, "invalid_level"
        level = level.strip().upper()

    basic_mechanism = _field(
        candidate, "basicMechanism", "basic_mechanism", "isBasicMechanism"
    )
    if basic_mechanism is None:
        basic_mechanism = False
    elif not isinstance(basic_mechanism, bool):
        return None, "invalid_basic_mechanism"

    resume_claim_id = _field(candidate, "resumeClaimId", "resume_claim_id")
    if resume_claim_id is not None and not isinstance(resume_claim_id, str):
        return None, "invalid_candidate"

    question_key = _field(candidate, "questionKey", "question_key")
    variant_id = _field(candidate, "variantId", "variant_id")
    origin_group_id = _field(candidate, "originGroupId", "origin_group_id")
    for value in (question_key, variant_id, origin_group_id):
        if value is not None and not isinstance(value, str):
            return None, "invalid_candidate"

    record: dict[str, object] = {
        "index": index,
        "card": candidate,
        "candidateId": candidate_id,
        "source": normalized_source,
        "rawSource": source_value,
        "projectId": project_id,
        "level": level,
        "basicMechanism": basic_mechanism,
        "resumeClaimId": resume_claim_id,
        "questionKey": question_key,
        "variantId": variant_id,
        "originGroupId": origin_group_id,
        "weakness": _weakness_card(candidate, normalized_source),
    }
    return record, None


def build_question_plan(
    spec: Mapping[str, object] | None = None, /, **overrides: object
) -> dict[str, list[dict[str, object]]]:
    """Select candidate cards under the active interview mode.

    ``spec`` may be one mapping (snake_case or the camelCase aliases used by
    the design document); keyword arguments are merged on top.  Returns
    ``{"selected": [...], "rejected": [...], "warnings": [...]}``.

    ``selected`` preserves the caller's card order and contains deep copies, so
    later editing never mutates the caller's plan.  ``rejected`` always carries
    a ``candidateId`` and a stable ``reason`` code; ``warnings`` carry a stable
    ``code`` and a human-readable ``detail``.
    """
    merged: dict[str, object] = {}
    if spec is not None:
        if not isinstance(spec, Mapping):
            raise QuestionPlanError("question plan spec must be a mapping")
        merged.update(spec)
    merged.update(overrides)

    mode = _field(merged, "mode")
    project_id = _field(merged, "project_id", "projectId")
    project_alias = _field(merged, "project_alias", "projectAlias")
    binding = _field(merged, "binding")
    resume_claims = _field(merged, "resume_claims", "resumeClaims")
    snapshot = _field(merged, "snapshot")
    candidates = _field(merged, "candidates")
    budget = _field(merged, "budget")

    if mode not in MODES:
        raise QuestionPlanError("mode must be full_mock or project_targeted")
    if type(budget) is not int or budget < 1:
        raise QuestionPlanError("budget must be a positive integer")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        raise QuestionPlanError("candidates must be a list of candidate cards")
    # A readable alias may only ever select the UUID the learning Skill already
    # confirmed.  Supplying one without its binding is ambiguous, and a mismatch
    # is a conflict: both fail closed instead of falling back to "last write".
    if project_alias is not None or binding is not None:
        resolved = resolve_target_project(binding, project_alias)
        if mode != MODE_PROJECT_TARGETED:
            raise QuestionPlanError("a project alias is only valid in project_targeted mode")
        if isinstance(project_id, str) and project_id.strip() and project_id.strip() != resolved["projectId"]:
            raise QuestionPlanError("alias binding and project_id disagree")
        project_id = project_id or resolved["projectId"]
    if mode == MODE_PROJECT_TARGETED:
        if not isinstance(project_id, str) or not project_id.strip():
            raise QuestionPlanError("project_targeted requires a non-empty project_id")
        project_id = project_id.strip()

    claims, warnings = _claimed_resume_ids(resume_claims)
    if not claims:
        warnings.append({
            "code": "non_resume_tailored",
            "detail": (
                "no confirmed resume claim: label this plan as not resume-tailored "
                "and never invent project experience"
            ),
        })

    rejected: list[dict[str, object]] = []
    eligible: list[dict[str, object]] = []
    for index, candidate in enumerate(candidates):
        record, reason = _read_candidate(candidate, index, mode)
        if record is None:
            rejected.append({
                "candidateId": f"candidate-{index}",
                "reason": reason or "invalid_candidate",
            })
            continue

        # A resume claim ID must come from the confirmed claim list; otherwise
        # the card would fabricate a resume link.  A full-mock resume bucket
        # without any confirmed claim is reported separately so the caller can
        # fall back to the 35/45/20 plan instead of inventing a claim.
        if (
            mode == MODE_FULL_MOCK
            and record["source"] == "resume_project"
            and not claims
        ):
            rejected.append({
                "candidateId": record["candidateId"],
                "reason": "no_confirmed_resume_claim",
            })
            continue
        claim_id = record["resumeClaimId"]
        if claim_id and claim_id not in claims:
            rejected.append({
                "candidateId": record["candidateId"],
                "reason": "unknown_resume_claim",
            })
            continue
        if mode == MODE_PROJECT_TARGETED and record["projectId"] != project_id:
            rejected.append({
                "candidateId": record["candidateId"],
                "reason": "project_mismatch",
            })
            continue
        eligible.append(record)

    # De-duplicate after per-card eligibility so a rejected card never consumes
    # a clue (for example an other-project repost).
    seen_ids: set[str] = set()
    seen_questions: set[tuple[str, str | None]] = set()
    seen_origin_groups: set[str] = set()
    unique: list[dict[str, object]] = []
    for record in eligible:
        if record["candidateId"] in seen_ids:
            rejected.append({"candidateId": record["candidateId"], "reason": "duplicate_candidate"})
            continue
        question_key = record["questionKey"]
        if isinstance(question_key, str) and question_key:
            question_signature = (question_key, record["variantId"] if isinstance(record["variantId"], str) else None)
            if question_signature in seen_questions:
                rejected.append({"candidateId": record["candidateId"], "reason": "duplicate_question"})
                continue
            seen_questions.add(question_signature)
        origin_group = record["originGroupId"]
        if isinstance(origin_group, str) and origin_group:
            if origin_group in seen_origin_groups:
                rejected.append({"candidateId": record["candidateId"], "reason": "duplicate_origin_group"})
                continue
            seen_origin_groups.add(origin_group)
        seen_ids.add(record["candidateId"])  # type: ignore[arg-type]
        unique.append(record)

    selected_cards: list[dict[str, object]] = []
    if mode == MODE_FULL_MOCK:
        selected_cards, quota_warnings = _select_full_mock(
            unique, budget, claims, rejected
        )
        warnings.extend(quota_warnings)
    else:
        selected_cards = _select_project_targeted(unique, budget, rejected)
        if snapshot is None:
            warnings.append({
                "code": "snapshot_missing",
                "detail": "project snapshot unavailable: selection uses only supplied candidate cards",
            })
        elif not isinstance(snapshot, Mapping):
            warnings.append({
                "code": "snapshot_unusable",
                "detail": "project snapshot was not an object and was not used",
            })
        else:
            snapshot_project = _field(snapshot, "projectId", "project_id")
            if (
                isinstance(snapshot_project, str)
                and snapshot_project.strip()
                and snapshot_project.strip() != project_id
            ):
                warnings.append({
                    "code": "snapshot_project_mismatch",
                    "detail": (
                        f"snapshot project {snapshot_project!r} does not match "
                        f"the selected project {project_id!r}; snapshot was not used"
                    ),
                })
        if (
            selected_cards
            and selected_cards[0]["level"] in {"L3", "L4"}
        ):
            warnings.append({
                "code": "targeted_plan_starts_above_l2",
                "detail": "project_targeted defaults to L2; only escalate to L3/L4 after actual answers",
            })

    if len(selected_cards) < budget:
        warnings.append({
            "code": "budget_shortfall",
            "detail": f"budget={budget} selected={len(selected_cards)}",
        })

    # Preserve the caller's priority order; quota grouping is a composition
    # decision, not an interview sequence.
    selected_cards.sort(key=lambda record: int(record["index"]))

    return {
        "selected": [deepcopy(dict(record["card"])) for record in selected_cards],
        "rejected": rejected,
        "warnings": warnings,
    }


def _select_full_mock(
    records: list[dict[str, object]],
    budget: int,
    claims: set[str],
    rejected: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    weights = dict(FULL_MOCK_WITH_RESUME if claims else FULL_MOCK_WITHOUT_RESUME)
    targets = _allocate(budget, weights)
    warnings: list[dict[str, str]] = []

    # The 40% weakness ceiling is absolute, even when the rounded quota asks
    # for more; the freed slots are re-allocated to the other main sources.
    ceiling = budget * 2 // WEAKNESS_CEILING_DIVISOR
    raw_weakness_target = targets["history_weakness"]
    if raw_weakness_target > ceiling:
        deficit = raw_weakness_target - ceiling
        targets["history_weakness"] = ceiling
        spare_weights = {
            name: weight for name, weight in weights.items() if name != "history_weakness"
        }
        for name, extra in _allocate(deficit, spare_weights).items():
            targets[name] += extra
        warnings.append({
            "code": "weakness_ceiling_applied",
            "detail": (
                f"weakness quota {raw_weakness_target} exceeded 40% of {budget}; "
                f"capped at {ceiling}"
            ),
        })

    buckets: dict[str, list[dict[str, object]]] = {name: [] for name in targets}
    for record in records:
        source = record["source"]
        if isinstance(source, str) and source in buckets:
            buckets[source].append(record)

    selected: list[dict[str, object]] = []
    selected_ids: set[str] = set()
    counts = {name: 0 for name in targets}
    weakness_selected = 0
    rejected_ids: set[str] = {
        str(item["candidateId"]) for item in rejected
    }
    for name, target in targets.items():
        for record in buckets[name]:
            candidate_id = str(record["candidateId"])
            if candidate_id in rejected_ids or candidate_id in selected_ids:
                continue
            if counts[name] >= target:
                rejected.append({"candidateId": candidate_id, "reason": "quota_exhausted"})
                rejected_ids.add(candidate_id)
                continue
            if record["weakness"] and weakness_selected >= ceiling:
                rejected.append({"candidateId": candidate_id, "reason": "weakness_ceiling"})
                rejected_ids.add(candidate_id)
                continue
            selected.append(record)
            selected_ids.add(candidate_id)
            counts[name] += 1
            if record["weakness"]:
                weakness_selected += 1

    for record in records:
        candidate_id = str(record["candidateId"])
        if candidate_id in selected_ids or candidate_id in rejected_ids:
            continue
        rejected.append({"candidateId": candidate_id, "reason": "quota_exhausted"})
        rejected_ids.add(candidate_id)

    for name, target in targets.items():
        if counts[name] < target:
            warnings.append({
                "code": "quota_shortfall",
                "detail": f"bucket={name} target={target} selected={counts[name]}",
            })
    return selected, warnings


def _select_project_targeted(
    records: list[dict[str, object]],
    budget: int,
    rejected: list[dict[str, object]],
) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    basic_selected = 0
    for record in records:
        candidate_id = str(record["candidateId"])
        if len(selected) >= budget:
            rejected.append({"candidateId": candidate_id, "reason": "budget_exhausted"})
            continue
        if record["basicMechanism"]:
            if basic_selected >= MAX_BASIC_MECHANISM_QUESTIONS:
                rejected.append({
                    "candidateId": candidate_id,
                    "reason": "basic_mechanism_limit",
                })
                continue
            basic_selected += 1
        selected.append(record)
    return selected
