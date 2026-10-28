"""Cross-language parity for the project interview contract (T1).

One synthetic fixture drives three implementations:

* the Python builder guard in ``reviewing-java-backend-interviews``;
* the Worker boundary in the runtime repository (via a Node harness);
* the shared JSON Schema (a local subset validator, standard library only).

The JSON Schema carries structure, enums and ranges. Cross-field arithmetic
(score sum, pass thresholds, evidence resolution against a live session) is
deliberately not expressible there; those cases are marked ``code_only`` and
are proven by the JS and Python implementations only.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
import re
import subprocess
import sys
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPOSITORY_ROOT / "tests" / "fixtures" / "project-interview-v1" / "scenario.json"
SCHEMA = REPOSITORY_ROOT / "conducting-java-backend-mock-interviews" / "schemas" / "contracts.schema.json"
REVIEW_SCRIPTS = REPOSITORY_ROOT / "reviewing-java-backend-interviews"
sys.path.insert(0, str(REVIEW_SCRIPTS))

from scripts.interview_core import (  # noqa: E402
    ReviewValidationError,
    validate_project_assessment,
    validate_project_review_event,
    validate_project_session_event,
)

RUNTIME_ROOT = Path(os.environ.get("RDS2_RUNTIME_ROOT", r"C:\Users\27846\my-chatgpt-mcp-v2"))
HARNESS = RUNTIME_ROOT / "services" / "reliable-drive-sync-worker" / "test" / "helpers" / "project-contract-harness.mjs"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def code_of(callable_) -> str | None:
    try:
        callable_()
    except ReviewValidationError as error:
        return error.code
    return None


def python_code(case: dict) -> str | None:
    kind = case["kind"]
    if kind == "session":
        return code_of(lambda: validate_project_session_event(case["event"]))
    if kind == "review":
        return code_of(lambda: validate_project_review_event(case["event"]))
    return code_of(lambda: validate_project_assessment(case["item"], case["question"]))


def build_cases(fixture: dict) -> list[dict]:
    session = fixture["baseSession"]
    review = fixture["baseReview"]
    question = session["questions"][0]
    assessment = review["questionReviews"][0]["projectAssessment"]
    cases: list[dict] = []

    def session_case(case_id, mutate, expected, *, schema=True):
        event = deepcopy(session)
        mutate(event)
        cases.append({
            "id": case_id, "kind": "session", "event": event,
            "expected": expected, "schema": schema,
        })

    def review_case(case_id, mutate, expected):
        event = deepcopy(review)
        mutate(event)
        cases.append({
            "id": case_id, "kind": "review", "event": event,
            "expected": expected, "schema": False,
        })

    def assessment_case(case_id, mutate, expected, *, target=None):
        item = {"questionId": "Q1", "projectAssessment": deepcopy(assessment)}
        mutate(item["projectAssessment"])
        cases.append({
            "id": case_id, "kind": "assessment", "item": item,
            "question": deepcopy(target or question), "expected": expected, "schema": False,
        })

    cases.append({
        "id": "legal-session", "kind": "session", "event": deepcopy(session),
        "expected": None, "schema": True,
    })
    session_case("unknown-evidence-field",
                 lambda event: event["questions"][0]["projectEvidence"].update({"extra": True}),
                 "invalid_project_evidence")
    session_case("daily-recap-purpose",
                 lambda event: event["questions"][0]["projectEvidence"].update({"purpose": "daily_recap"}),
                 "invalid_project_evidence")
    session_case("assistant-answer",
                 lambda event: event["questions"][0]["projectEvidence"]["provenance"].update(
                     {"answerOrigin": "assistant"}),
                 "invalid_project_evidence")
    session_case("empty-variant-axes",
                 lambda event: event["questions"][0]["projectEvidence"].update({"variantAxes": []}),
                 "invalid_project_evidence")

    def learning_plain_question(event):
        plain = deepcopy(event["questions"][0])
        plain["questionId"] = "Q2"
        plain.pop("projectEvidence")
        event["questions"].append(plain)

    session_case("learning-requires-evidence", learning_plain_question, "invalid_project_evidence")

    def missing_version(event):
        event.pop("projectContractVersion")

    session_case("learning-without-version", missing_version, "project_contract_version_unsupported")

    def duplicate_attempt(event):
        again = deepcopy(event["questions"][0])
        again["questionId"] = "Q2"
        event["questions"].append(again)

    session_case("duplicate-attempt-in-session", duplicate_attempt, "attempt_identity_conflict", schema=False)

    def oversized_question(event):
        event["questions"][0]["originalAnswer"] = "答" * 9000

    session_case("oversized-question", oversized_question, "project_envelope_too_large", schema=False)

    cases.append({
        "id": "legal-review", "kind": "review", "event": deepcopy(review),
        "expected": None, "schema": True,
    })
    review_case("learning-review-profile-changes",
                lambda event: event.update({"profileChanges": [{"kind": "weakness", "outcome": "failed"}]}),
                "invalid_project_evidence")

    def duplicate_review_attempt(event):
        item = deepcopy(event["questionReviews"][0])
        item["questionId"] = "Q2"
        event["questionReviews"].append(item)

    review_case("duplicate-review-attempt", duplicate_review_attempt, "assessment_question_mismatch")

    cases.append({
        "id": "legal-assessment", "kind": "assessment",
        "item": {"questionId": "Q1", "projectAssessment": deepcopy(assessment)},
        "question": deepcopy(question), "expected": None, "schema": False,
    })
    assessment_case("score-over-cap",
                    lambda value: value.update({
                        "scores": {"technical": 31, "projectEvidence": 17, "causal": 10,
                                   "tradeoff": 9, "expression": 8}, "total": 75}),
                    "invalid_project_evidence")
    assessment_case("total-mismatch", lambda value: value.update({"total": 63}), "invalid_project_evidence")
    assessment_case("passed-below-threshold",
                    lambda value: value.update({
                        "scores": {"technical": 24, "projectEvidence": 18, "causal": 14,
                                   "tradeoff": 10, "expression": 9},
                        "total": 75, "outcome": "passed"}),
                    "invalid_project_evidence")
    assessment_case("evidence-target-missing",
                    lambda value: value.update({"evidenceRefs": ["Q1:timeline:missing"]}),
                    "assessment_evidence_unresolvable")
    assessment_case("attempt-mismatch",
                    lambda value: value.update({"attemptId": "33333333-3333-4333-8333-000000000099"}),
                    "assessment_question_mismatch")

    plain_question = deepcopy(question)
    plain_question.pop("projectEvidence")
    cases.append({
        "id": "assessment-without-project-question", "kind": "assessment",
        "item": {"questionId": "Q1", "projectAssessment": deepcopy(assessment)},
        "question": plain_question, "expected": "review_source_mismatch", "schema": False,
    })
    assessment_case("oversized-assessment",
                    lambda value: value.update({"reason": "说" * 2800}),
                    "project_envelope_too_large")
    return cases


def run_javascript(cases: list[dict]) -> dict[str, str | None]:
    if not HARNESS.is_file():
        raise unittest.SkipTest("runtime_root_unavailable")
    payload = {"cases": [
        {key: case[key] for key in ("id", "kind", "event", "item", "question") if key in case}
        for case in cases
    ]}
    completed = subprocess.run(
        ["node", str(HARNESS)],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    if completed.returncode != 0:
        raise AssertionError(f"node harness failed: {completed.stderr}")
    results = json.loads(completed.stdout)["results"]
    return {entry["id"]: entry["code"] for entry in results}


# ---------------------------------------------------------------------------
# Minimal JSON Schema (2020-12 subset) validator for the shared contract file.
# Formats are not enforced here; the Worker boundary owns them.
# ---------------------------------------------------------------------------
def schema_errors(instance: object, schema: dict, root: dict, path: str = "$") -> list[str]:
    errors: list[str] = []
    if "$ref" in schema:
        target = root
        for part in schema["$ref"].lstrip("#/").split("/"):
            target = target[part]
        return schema_errors(instance, target, root, path)
    if "type" in schema:
        allowed = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_matches(instance, name) for name in allowed):
            return [f"{path}: expected {allowed}"]
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: const")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: enum")
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: minLength")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: maxLength")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            errors.append(f"{path}: pattern")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: minItems")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: maxItems")
        if "items" in schema:
            for index, item in enumerate(instance):
                errors.extend(schema_errors(item, schema["items"], root, f"{path}[{index}]"))
    if isinstance(instance, dict):
        for name in schema.get("required", []):
            if name not in instance:
                errors.append(f"{path}: required {name}")
        properties = schema.get("properties", {})
        for name, value in instance.items():
            if name in properties:
                errors.extend(schema_errors(value, properties[name], root, f"{path}.{name}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: additional {name}")
    for sub in schema.get("allOf", []):
        errors.extend(schema_errors(instance, sub, root, path))
    if "not" in schema:
        if not schema_errors(instance, schema["not"], root, path):
            errors.append(f"{path}: not")
    if "if" in schema:
        matched = not schema_errors(instance, schema["if"], root, path)
        branch = schema.get("then") if matched else schema.get("else")
        if branch:
            errors.extend(schema_errors(instance, branch, root, path))
    if "oneOf" in schema:
        passing = [sub for sub in schema["oneOf"]
                   if not schema_errors(instance, sub, root, path)]
        if len(passing) != 1:
            errors.append(f"{path}: oneOf")
    return errors


def _type_matches(value: object, name: str) -> bool:
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "string":
        return isinstance(value, str)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "null":
        return value is None
    return True


class ProjectContractParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = load_fixture()
        cls.cases = build_cases(cls.fixture)
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def test_fixture_is_marked_synthetic(self) -> None:
        self.assertIs(self.fixture["fixtureOnly"], True)
        self.assertEqual(self.fixture["proposedContractVersion"], 1)

    def test_python_matches_expected_codes(self) -> None:
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(python_code(case), case["expected"])

    def test_javascript_matches_python(self) -> None:
        js_codes = run_javascript(self.cases)
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(js_codes[case["id"]], case["expected"],
                                 f"JS disagreed for {case['id']}")

    def test_schema_agrees_on_structural_cases(self) -> None:
        for case in self.cases:
            if not case.get("schema"):
                continue
            instance = case.get("event", case.get("item"))
            passed = not schema_errors(instance, self.schema["$defs"][
                "SessionEvent" if case["kind"] == "session" else "ReviewEvent"
            ], self.schema)
            expected_pass = case["expected"] is None
            with self.subTest(case=case["id"]):
                self.assertEqual(passed, expected_pass,
                                 f"schema disagreed for {case['id']}")
