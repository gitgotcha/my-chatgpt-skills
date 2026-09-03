"""Build and validate person-protected per-image edit plans."""
from __future__ import annotations

import argparse
import copy
import json

MODES = {"background-only", "skin-only", "crop-only", "theme-edit", "poster-edit", "batch-style-transfer"}
DEFAULT_OUTPUT_SPEC = {"ratio": "3:5", "width": 1200, "height": 2000}
ALLOWED_REGIONS = {
    "background-only": ["background"],
    "skin-only": ["skin-tone-adjustments"],
    "crop-only": ["crop-canvas"],
    "theme-edit": ["background", "peripheral-elements", "safe-text-zones"],
    "poster-edit": ["background", "peripheral-elements", "safe-text-zones"],
    "batch-style-transfer": ["background", "peripheral-elements", "safe-text-zones"],
}
REQUEST_FIELDS = {
    "background-only": {"background"},
    "skin-only": {"skinToneAdjustments"},
    "crop-only": {"crop"},
    "theme-edit": {"background", "peripheralElements", "textSafeZones"},
    "poster-edit": {"background", "peripheralElements", "text", "textSafeZones"},
    "batch-style-transfer": {"background", "peripheralElements", "text", "textSafeZones", "compositionAdaptation"},
}
IMMUTABLE = [
    "face", "facial-features", "head-shape", "eyes", "eye-spacing", "nose", "mouth", "ears",
    "hairline", "hair", "body-proportions", "limb-proportions", "hands-feet", "age", "pose", "action", "original-expression",
]
REQUIRED_PROTECTED = {"entire-person", "original-expression"}
PERSON_MUTATING_FIELDS = {
    "replaceface", "face", "facialfeatures", "faceshape", "headshape", "eyes", "eyeshape", "eyespacing",
    "nose", "mouth", "mouthshape", "ears", "hairline", "hair", "hairstyle", "hairamount", "bodyproportions",
    "limbproportions", "hands", "feet", "handsfeet", "age", "pose", "action", "expression", "originalexpression",
}


def _normalize_output_spec(output_spec):
    if output_spec is None:
        output_spec = {}
    if not isinstance(output_spec, dict):
        raise ValueError("outputSpec must be an object")
    unknown = set(output_spec) - set(DEFAULT_OUTPUT_SPEC)
    if unknown:
        raise ValueError(f"outputSpec contains unknown fields: {sorted(unknown)}")
    normalized = {**DEFAULT_OUTPUT_SPEC, **copy.deepcopy(output_spec)}
    if not isinstance(normalized["ratio"], str) or not normalized["ratio"].strip():
        raise ValueError("outputSpec ratio must be a non-empty string")
    for field in ("width", "height"):
        value = normalized[field]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"outputSpec {field} must be a positive integer")
    return normalized


def _validate_requested_changes(mode, requested_changes):
    if not isinstance(requested_changes, dict):
        raise ValueError("requestedChanges must be an object")
    rejected = set(requested_changes) - REQUEST_FIELDS[mode]
    if rejected:
        raise ValueError(f"requestedChanges fields are not allowed for {mode}: {sorted(rejected)}")
    pending = list(requested_changes.values())
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            for key, nested in value.items():
                normalized_key = "".join(character for character in str(key).lower() if character.isalnum())
                if normalized_key in PERSON_MUTATING_FIELDS:
                    raise ValueError(f"requestedChanges contains person-mutating field: {key}")
                pending.append(nested)
        elif isinstance(value, (list, tuple)):
            pending.extend(value)
    return copy.deepcopy(requested_changes)


def build_edit_plan(source_id, mode, pose, expression, output_spec, requested_changes):
    if mode not in MODES:
        raise ValueError(f"full-frame or unknown mode is forbidden: {mode}")
    normalized_output = _normalize_output_spec(output_spec)
    normalized_changes = _validate_requested_changes(mode, requested_changes)
    plan = {
        "sourceId": source_id,
        "mode": mode,
        "pose": pose,
        "expression": expression,
        "protectedRegions": ["entire-person", "face", "hair", "hands-feet", "original-expression"],
        "allowedRegions": list(ALLOWED_REGIONS[mode]),
        "crop": copy.deepcopy(normalized_output),
        "textSafeZones": copy.deepcopy(normalized_changes.get("textSafeZones", [])),
        "requestedChanges": normalized_changes,
        "forbiddenOperations": list(IMMUTABLE),
        "preserveCrying": expression == "crying",
        "outputSpec": normalized_output,
    }
    return validate_edit_plan(plan)


def validate_edit_plan(plan: dict) -> dict:
    if not isinstance(plan, dict):
        raise ValueError("edit plan must be an object")
    result = copy.deepcopy(plan)
    mode = result.get("mode")
    if mode not in MODES:
        raise ValueError(f"full-frame or unknown mode is forbidden: {mode}")
    forbidden = result.get("forbiddenOperations", [])
    if not isinstance(forbidden, list) or not all(isinstance(value, str) for value in forbidden):
        raise ValueError("forbidden operations must be a string list")
    if not set(IMMUTABLE).issubset(set(forbidden)):
        raise ValueError("person authenticity lock is incomplete")
    protected = result.get("protectedRegions", [])
    if not isinstance(protected, list) or not all(isinstance(value, str) for value in protected):
        raise ValueError("protected regions must be a string list")
    if not REQUIRED_PROTECTED.issubset(set(protected)):
        raise ValueError("required protected regions are missing")
    if result.get("allowedRegions") != ALLOWED_REGIONS[mode]:
        raise ValueError(f"allowed regions for {mode} must equal {ALLOWED_REGIONS[mode]}")
    result["requestedChanges"] = _validate_requested_changes(mode, result.get("requestedChanges", {}))
    result["outputSpec"] = _normalize_output_spec(result.get("outputSpec"))
    result["crop"] = copy.deepcopy(result["outputSpec"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a person-protected edit plan")
    parser.add_argument("plan", nargs="?", help="JSON plan file")
    args = parser.parse_args()
    if args.plan:
        try:
            with open(args.plan, encoding="utf-8") as plan_file:
                plan = json.load(plan_file)
            validated = validate_edit_plan(plan)
        except json.JSONDecodeError as exc:
            parser.error(f"invalid JSON in {args.plan}: {exc.msg}")
        except OSError as exc:
            parser.error(f"cannot read plan {args.plan}: {exc}")
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(validated, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
