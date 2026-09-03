"""Build and validate person-protected per-image edit plans."""
from __future__ import annotations

import argparse
import json

MODES = {"background-only", "skin-only", "crop-only", "theme-edit", "poster-edit", "batch-style-transfer"}
IMMUTABLE = [
    "face", "facial-features", "head-shape", "eyes", "eye-spacing", "nose", "mouth", "ears",
    "hairline", "hair", "body-proportions", "limb-proportions", "hands-feet", "age", "pose", "action", "original-expression",
]


def build_edit_plan(source_id, mode, pose, expression, output_spec, requested_changes):
    allowed = {
        "background-only": ["background"],
        "skin-only": ["skin-tone-adjustments"],
        "crop-only": ["crop-canvas"],
        "theme-edit": ["background", "peripheral-elements", "safe-text-zones"],
        "poster-edit": ["background", "peripheral-elements", "safe-text-zones"],
        "batch-style-transfer": ["background", "peripheral-elements", "safe-text-zones"],
    }
    plan = {
        "sourceId": source_id,
        "mode": mode,
        "pose": pose,
        "expression": expression,
        "protectedRegions": ["entire-person", "face", "hair", "hands-feet", "original-expression"],
        "allowedRegions": allowed.get(mode, []),
        "crop": {"ratio": output_spec.get("ratio", "3:5"), "width": output_spec.get("width", 1200), "height": output_spec.get("height", 2000)},
        "textSafeZones": requested_changes.get("textSafeZones", []),
        "requestedChanges": requested_changes,
        "forbiddenOperations": list(IMMUTABLE),
        "preserveCrying": expression == "crying",
        "outputSpec": output_spec,
    }
    return validate_edit_plan(plan)


def validate_edit_plan(plan: dict) -> dict:
    mode = plan.get("mode")
    if mode not in MODES:
        raise ValueError(f"full-frame or unknown mode is forbidden: {mode}")
    if not set(IMMUTABLE).issubset(set(plan.get("forbiddenOperations", []))):
        raise ValueError("person authenticity lock is incomplete")
    if mode == "background-only" and plan.get("allowedRegions") != ["background"]:
        raise ValueError("background-only must allow background only")
    if mode == "skin-only" and plan.get("allowedRegions") != ["skin-tone-adjustments"]:
        raise ValueError("skin-only must allow skin tone adjustments only")
    if mode == "crop-only" and plan.get("allowedRegions") != ["crop-canvas"]:
        raise ValueError("crop-only must allow crop canvas only")
    if "entire-frame" in plan.get("allowedRegions", []) or mode == "full-frame":
        raise ValueError("full-frame regeneration is forbidden")
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a person-protected edit plan")
    parser.add_argument("plan", nargs="?", help="JSON plan file")
    args = parser.parse_args()
    if args.plan:
        print(json.dumps(validate_edit_plan(json.load(open(args.plan, encoding="utf-8"))), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
