"""Compile person-protected generation instructions."""
from __future__ import annotations

import argparse
import copy
import json

from style_profile import validate_approved_hints
from validate_edit_plan import validate_edit_plan

NEGATIVE_CONSTRAINTS = (
    "no face replacement; no changes to facial features, face shape, head shape, eye shape, "
    "eye spacing, nose, mouth shape, ears, hairline, hairstyle, hair amount, body proportions, "
    "limb proportions, hands or feet, age, pose, action, clothing, or original expression; "
    "preserve crying; no full-frame regeneration; do not cover the person with text or elements"
)


def _serialize_authority_then_methods(profile: dict, plan: dict) -> str:
    authority = json.dumps(profile.get("styleAuthority", {}), ensure_ascii=False, sort_keys=True)
    methods = json.dumps(profile.get("approvedTreatmentHints", {}), ensure_ascii=False, sort_keys=True)
    return (
        f"Current Style Authority (source of colors, theme, background, light, elements, typography, texture and composition): {authority}. "
        f"Approved Treatment Hints (execution quality only; never infer style values): {methods}. "
        f"Edit only allowed regions {plan.get('allowedRegions', [])}; protect the entire person and adapt to the source pose."
    )


def build_prompt(profile: dict, plan: dict) -> dict:
    if not isinstance(profile, dict):
        raise ValueError("style profile must be an object")
    validated_profile = copy.deepcopy(profile)
    validated_profile["approvedTreatmentHints"] = validate_approved_hints(profile.get("approvedTreatmentHints", {}))
    validated_plan = validate_edit_plan(plan)
    mode = validated_plan["mode"]
    return {
        "instruction": _serialize_authority_then_methods(validated_profile, validated_plan),
        "negativeConstraints": NEGATIVE_CONSTRAINTS,
        "maskPolicy": mode if mode in {"background-only", "skin-only", "crop-only"} else "person-protected-periphery",
        "outputSpec": validated_plan["outputSpec"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a safe generation prompt")
    parser.add_argument("profile")
    parser.add_argument("plan")
    args = parser.parse_args()
    try:
        with open(args.profile, encoding="utf-8") as profile_file:
            profile = json.load(profile_file)
        with open(args.plan, encoding="utf-8") as plan_file:
            plan = json.load(plan_file)
        prompt = build_prompt(profile, plan)
    except json.JSONDecodeError as exc:
        parser.error(f"invalid JSON: {exc.msg}")
    except OSError as exc:
        parser.error(f"cannot read input file: {exc}")
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(prompt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
