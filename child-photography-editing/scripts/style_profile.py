"""Compile a current style authority with dimension-scoped treatment hints."""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from typing import Any

ALLOWED_HINTS = {
    "skin": {"brightness_delta_percent", "texture_preservation", "natural_blush_strength", "eye_refresh"},
    "background": {"edge_cleanliness", "shadow_integration", "depth_quality", "simplicity"},
    "elements": {"density", "scale_balance", "subject_avoidance", "childlike_tone"},
    "layout": {"negative_space_use", "text_safe_zone", "hierarchy"},
}


def validate_approved_hints(hints: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if not isinstance(hints, dict):
        raise ValueError("approved treatment hints must be an object")
    result = deepcopy(hints)
    for section, values in result.items():
        if section not in ALLOWED_HINTS:
            raise ValueError(f"style-bearing section is not allowed: {section}")
        if not isinstance(values, dict):
            raise ValueError(f"style-bearing section must be an object: {section}")
        rejected = set(values) - ALLOWED_HINTS[section]
        if rejected:
            raise ValueError(f"style-bearing fields are not allowed: {sorted(rejected)}")
        if section == "skin":
            if "brightness_delta_percent" in values:
                values["brightness_delta_percent"] = min(5, max(3, float(values["brightness_delta_percent"])))
                if float(values["brightness_delta_percent"]).is_integer():
                    values["brightness_delta_percent"] = int(values["brightness_delta_percent"])
            if values.get("eye_refresh") not in (None, "none", "subtle"):
                values["eye_refresh"] = "subtle"
    return result


def compile_style_profile(observations: dict, overrides: dict, approved_hints: dict) -> dict:
    authority = deepcopy(observations or {})
    authority.update(deepcopy(overrides or {}))
    return {
        "schemaVersion": "1.0",
        "styleAuthority": authority,
        "approvedTreatmentHints": validate_approved_hints(approved_hints or {}),
        "precedence": ["personAuthenticity", "currentRequest", "newReference", "approvedTreatment", "defaultRecipe"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile a style profile from JSON")
    parser.add_argument("--observations", default="{}")
    parser.add_argument("--overrides", default="{}")
    parser.add_argument("--approved-hints", default="{}")
    args = parser.parse_args()
    profile = compile_style_profile(json.loads(args.observations), json.loads(args.overrides), json.loads(args.approved_hints))
    print(json.dumps(profile, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
