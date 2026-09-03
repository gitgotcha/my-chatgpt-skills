"""Compile person-protected generation instructions."""
from __future__ import annotations

import argparse
import json

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
    mode = plan.get("mode")
    return {
        "instruction": _serialize_authority_then_methods(profile, plan),
        "negativeConstraints": NEGATIVE_CONSTRAINTS,
        "maskPolicy": mode if mode in {"background-only", "skin-only", "crop-only"} else "person-protected-periphery",
        "outputSpec": plan.get("outputSpec", {"ratio": "3:5", "width": 1200, "height": 2000}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a safe generation prompt")
    parser.add_argument("profile")
    parser.add_argument("plan")
    args = parser.parse_args()
    profile = json.load(open(args.profile, encoding="utf-8"))
    plan = json.load(open(args.plan, encoding="utf-8"))
    print(json.dumps(build_prompt(profile, plan), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
