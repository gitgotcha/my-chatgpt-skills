"""Compile a current style authority with dimension-scoped treatment hints."""
from __future__ import annotations

import argparse
import json
import math
from copy import deepcopy
from typing import Any

HINT_VALUE_SCHEMAS = {
    "skin": {
        "brightness_delta_percent": ("number", 3, 5),
        "texture_preservation": frozenset({"natural", "high"}),
        "natural_blush_strength": frozenset({"none", "subtle"}),
        "eye_refresh": frozenset({"none", "subtle", "strong"}),
    },
    "background": {
        "edge_cleanliness": frozenset({"natural", "high"}),
        "shadow_integration": frozenset({"natural", "seamless"}),
        "depth_quality": frozenset({"subtle", "balanced", "high"}),
        "simplicity": frozenset({"low", "medium", "high"}),
    },
    "elements": {
        "density": frozenset({"light", "balanced"}),
        "scale_balance": frozenset({"balanced"}),
        "subject_avoidance": frozenset({"strict"}),
        "childlike_tone": frozenset({"subtle", "balanced"}),
    },
    "layout": {
        "negative_space_use": frozenset({"balanced", "generous"}),
        "text_safe_zone": frozenset({"strict"}),
        "hierarchy": frozenset({"clear", "balanced"}),
    },
}
ALLOWED_HINTS = {section: set(fields) for section, fields in HINT_VALUE_SCHEMAS.items()}


def _normalize_hint_value(section: str, field: str, value: Any) -> Any:
    schema = HINT_VALUE_SCHEMAS[section][field]
    if isinstance(schema, tuple) and schema[0] == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"invalid treatment value for {section}.{field}: expected a number")
        normalized = min(schema[2], max(schema[1], float(value)))
        return int(normalized) if normalized.is_integer() else normalized
    if not isinstance(value, str) or value not in schema:
        raise ValueError(f"invalid treatment value for {section}.{field}: {value!r}")
    if section == "skin" and field == "eye_refresh" and value == "strong":
        return "subtle"
    return value


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
        for field, value in values.items():
            values[field] = _normalize_hint_value(section, field, value)
    return result


def _evidence_value(raw_value: Any, kind: str, default_source: str, default_confidence: float):
    value = deepcopy(raw_value)
    source = default_source
    confidence = default_confidence
    if isinstance(raw_value, dict) and "value" in raw_value:
        unknown = set(raw_value) - {"value", "source", "confidence"}
        if unknown:
            raise ValueError(f"style evidence contains unknown fields: {sorted(unknown)}")
        value = deepcopy(raw_value["value"])
        source = raw_value.get("source", default_source)
        confidence = raw_value.get("confidence", default_confidence)
    if not isinstance(source, str) or not source.strip():
        raise ValueError("style evidence source must be a non-empty string")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise ValueError("style evidence confidence must be within [0,1]")
    return value, {"kind": kind, "source": source, "confidence": float(confidence)}


def _apply_style_values(authority, evidence, values, kind, source, confidence, overwrite):
    if values is None:
        return
    if not isinstance(values, dict):
        raise ValueError(f"{kind} style values must be an object")
    for dimension, raw_value in values.items():
        if overwrite or dimension not in authority:
            value, entry = _evidence_value(raw_value, kind, source, confidence)
            authority[dimension] = value
            evidence[dimension] = entry


def compile_style_profile(observations: dict, overrides: dict, approved_hints: dict, inferences: dict | None = None) -> dict:
    authority = {}
    evidence = {}
    _apply_style_values(authority, evidence, observations or {}, "observed", "developerReferences", 1.0, True)
    _apply_style_values(authority, evidence, inferences or {}, "inferred", "styleInference", 0.5, False)
    _apply_style_values(authority, evidence, overrides or {}, "user-override", "currentUserRequest", 1.0, True)
    return {
        "schemaVersion": "1.0",
        "styleAuthority": authority,
        "styleEvidence": evidence,
        "approvedTreatmentHints": validate_approved_hints(approved_hints or {}),
        "precedence": ["personAuthenticity", "currentRequest", "newReference", "approvedTreatment", "defaultRecipe"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile a style profile from JSON")
    parser.add_argument("--observations", default="{}")
    parser.add_argument("--inferences", default="{}")
    parser.add_argument("--overrides", default="{}")
    parser.add_argument("--approved-hints", default="{}")
    args = parser.parse_args()
    try:
        profile = compile_style_profile(
            json.loads(args.observations),
            json.loads(args.overrides),
            json.loads(args.approved_hints),
            json.loads(args.inferences),
        )
    except json.JSONDecodeError as exc:
        parser.error(f"invalid JSON: {exc.msg}")
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(profile, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
