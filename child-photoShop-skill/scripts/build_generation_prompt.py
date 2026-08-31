#!/usr/bin/env python3
"""Compile a Style Profile into an image-generation prompt.

This script does NOT generate anything.  It turns the numbers that
``style_profile.py learn`` measured into words an image model understands, and
it attaches the negative constraints that a children's portrait demands.

Why this exists
---------------
An image model cannot be handed a JSON of floats, and an agent asked to
"write a prompt from this profile" improvises differently every time.  The
mapping from measurement to wording is deterministic and worth fixing: the
same profile must always produce the same prompt, so that a batch of photos
is graded and generated consistently.

The second half of the job is the part an agent is worst at -- remembering
every prohibition.  Every prompt this script emits carries the full identity,
childhood, expression and artifact negative list, whether or not the profile
mentioned them.

Usage
-----
    python build_generation_prompt.py --profile style.json
    python build_generation_prompt.py --profile style.json --mode background_only
    python build_generation_prompt.py --profile style.json --diff compare.json --json

Modes
-----
reference_board
    Generate a style/mood board only.  No photograph of a child is involved,
    so nothing is at risk.  This is the recommended use of a generative
    backend in a children's workflow.
background_only
    Regenerate the background behind the child.  The prompt says so
    explicitly and the child is described as a region to keep untouched.
full_frame
    Regenerate the whole frame.  Emitted with a loud warning: this is
    "Full Regeneration", which SKILL.md section 12 excludes from standard
    retouching.  Use only for Creative Edit with explicit confirmation.

Dependencies: none beyond the standard library (the profile is already JSON).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Sequence

MODES = ("reference_board", "background_only", "full_frame")

# Prohibitions that hold for every children's portrait, in every mode.  They
# are not negotiable and they are not inferred from the profile -- they are
# the floor.  See references/identity-preservation.md and
# references/childhood-preservation.md.
IDENTITY_NEGATIVES = [
    "changed face shape",
    "different child",
    "aged-up face",
    "adult facial structure",
    "slimmer face",
    "V-line jaw",
    "enlarged eyes",
    "eye corner opening",
    "reshaped nose",
    "plumped lips",
    "whitened teeth veneers",
    "changed hairstyle or hairline",
    "changed eye colour",
]

EXPRESSION_NEGATIVES = [
    "posed smile replacing the real expression",
    "mouth closed where it was open",
    "standardised grin",
    "looking at camera where the child looked away",
    "calm serene expression replacing laughter",
]

CHILDHOOD_NEGATIVES = [
    "adult makeup",
    "eyeliner",
    "false eyelashes",
    "contouring",
    "mature styling",
    "fashion-model posing",
    "sexy or glamour styling",
]

ARTIFACT_NEGATIVES = [
    "extra fingers",
    "fused fingers",
    "missing fingers",
    "deformed hands",
    "warped clothing",
    "duplicated toy",
    "garbled text",
    "halo around the subject",
    "plastic waxy skin",
    "over-smoothed skin",
    "halo artifacts",
    "oversharpened edges",
]

STRUCTURAL_NEGATIVES = [
    "watermark",
    "signature",
    "logo",
    "frame border",
    "text overlay",
]

MODE_NOTES = {
    "reference_board": (
        "Style/mood board. No photograph is being edited, so no identity is at "
        "risk. Use this to show the client the look before touching a frame."
    ),
    "background_only": (
        "Regenerate ONLY the background. The child, the face, the hair, the "
        "hands and the clothing are a protected region -- describe them as "
        "untouched, mask them out, and keep denoise low."
    ),
    "full_frame": (
        "FULL REGENERATION. SKILL.md section 12 excludes this from standard "
        "retouching. Proceed only under Creative Edit Mode with explicit user "
        "confirmation, and verify identity afterwards."
    ),
}

# Denoise / strength ceilings per mode.  These are ceilings, not targets: a
# children's portrait wants the lowest value that still does the job.
MODE_STRENGTH = {
    "reference_board": 1.0,
    "background_only": 0.45,
    "full_frame": 0.35,
}


def _section(profile: Dict[str, Any], name: str) -> Dict[str, Any]:
    """Return a named section, or an empty dict.

    ``profile.get(name, {})`` is not enough: it returns the default only when
    the key is ABSENT.  A key present with the value ``None`` -- which is what
    JSON round-trips give you for a null section -- returns ``None``, and the
    following ``.get`` raises.  A profile is untrusted input; it may have been
    hand-edited or produced by a different generator version.
    """
    value = profile.get(name)
    return value if isinstance(value, dict) else {}


def _get(profile: Dict[str, Any], section: str, key: str, default: Any = 0.0) -> float:
    try:
        value = _section(profile, section).get(key, default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _band(value: float, low: float, high: float) -> str:
    if value < low:
        return "low"
    if value > high:
        return "high"
    return "mid"


def lighting_words(profile: Dict[str, Any]) -> List[str]:
    softness = _get(profile, "lighting", "softness")
    mean_luma = _get(profile, "exposure", "mean_luma")
    shadow_depth = _get(profile, "lighting", "shadow_depth")
    direction = str(_section(profile, "lighting").get("direction", "unknown"))

    words: List[str] = []
    if softness > 0.6:
        words.append("large soft light source, soft wraparound light, gentle shadow transition")
    elif softness > 0.35:
        words.append("soft diffused light, moderate shadow transition")
    else:
        words.append("directional light, defined but not harsh shadow transition")

    if mean_luma > 0.62:
        words.append("bright airy high-key exposure")
    elif mean_luma > 0.45:
        words.append("balanced mid-key exposure")
    else:
        words.append("moody low-key exposure")

    if shadow_depth > 0.35:
        words.append("deep blacks in the shadows")
    elif shadow_depth < 0.18:
        words.append("lifted milky shadows, low-contrast shadow region")

    direction_map = {
        "top": "light falling from above",
        "left": "light from the left",
        "right": "light from the right",
        "bottom": "light from below",
        "front": "frontal light",
        "flat": "even flat light with no dominant direction",
    }
    if direction in direction_map:
        words.append(direction_map[direction])
    return words


def color_words(profile: Dict[str, Any]) -> List[str]:
    warmth = str(_section(profile, "white_balance").get("temperature_hint", "neutral"))
    saturation = _get(profile, "color", "mean_saturation")
    skin_hex = str(_section(profile, "skin").get("tone_hex", ""))

    words: List[str] = []
    if warmth == "warm":
        words.append("warm amber golden colour temperature")
    elif warmth == "cool":
        words.append("cool blue-teal colour temperature")
    else:
        words.append("neutral balanced colour temperature")

    if saturation > 0.45:
        words.append("rich saturated colour")
    elif saturation > 0.28:
        words.append("natural moderate colour saturation")
    else:
        words.append("muted desaturated colour")

    hues = _section(profile, "color").get("dominant_hues") or []
    if isinstance(hues, list) and hues:
        names = [_hue_name(int(h)) for h in hues[:3]]
        words.append("dominant tones: " + ", ".join(n for n in names if n))

    if skin_hex:
        words.append("skin tone near {}".format(skin_hex))
    return words


def _hue_name(degrees: int) -> str:
    table = [
        (15, "red"),
        (45, "orange"),
        (70, "yellow"),
        (160, "green"),
        (200, "cyan"),
        (255, "blue"),
        (290, "purple"),
        (330, "magenta"),
        (360, "red"),
    ]
    for limit, name in table:
        if degrees < limit:
            return name
    return "red"


def tone_words(profile: Dict[str, Any]) -> List[str]:
    contrast = _get(profile, "exposure", "contrast")
    shadow_lift = _get(profile, "exposure", "shadow_lift")
    highlight_rolloff = _get(profile, "exposure", "highlight_rolloff")
    vignette = _get(profile, "background", "vignette")

    words: List[str] = []
    if contrast > 0.24:
        words.append("punchy contrast")
    elif contrast > 0.16:
        words.append("medium contrast")
    else:
        words.append("soft flat contrast")

    if shadow_lift > 0.3:
        words.append("crushed-free lifted blacks")
    if highlight_rolloff > 0.9:
        words.append("smooth highlight roll-off, no clipped whites")
    if vignette > 0.02:
        words.append("subtle vignette")
    return words


def texture_words(profile: Dict[str, Any]) -> List[str]:
    grain = _get(profile, "texture", "grain")
    microcontrast = _get(profile, "texture", "microcontrast")
    halation = _get(profile, "texture", "halation")

    words: List[str] = []
    if grain > 0.02:
        words.append("fine film grain")
    else:
        words.append("clean grain-free rendering")

    if microcontrast > 0.35:
        words.append("crisp microcontrast, tactile detail")
    elif microcontrast < 0.12:
        words.append("smooth low microcontrast")

    if halation > 0.25:
        words.append("gentle halation around highlights")
    return words


def background_words(profile: Dict[str, Any]) -> List[str]:
    bg_hex = str(_section(profile, "background").get("tone_hex", ""))
    words: List[str] = []
    if bg_hex:
        words.append("background in the region of {}".format(bg_hex))
    mood = profile.get("mood") or []
    if isinstance(mood, list) and mood:
        words.extend(str(m) for m in mood)
    return words


def intent_words(intent: str) -> List[str]:
    """Map a short user instruction onto prompt wording.

    The iteration vocabulary is small and fixed; an unknown instruction is
    passed through verbatim rather than silently dropped, because dropping a
    client's words is worse than passing them along untranslated.
    """
    table = {
        "再暖一点": "slightly warmer colour temperature",
        "再冷一点": "slightly cooler colour temperature",
        "再亮一点": "slightly brighter exposure",
        "再暗一点": "slightly darker exposure",
        "再艳一点": "slightly more saturated colour",
        "再淡一点": "slightly less saturated colour",
        "对比再强一点": "slightly stronger contrast",
        "对比再弱一点": "slightly softer contrast",
        "背景再干净点": "cleaner simpler background",
        "再柔一点": "softer light, gentler shadow transition",
        "颗粒再大一点": "more visible film grain",
    }
    key = (intent or "").strip()
    if not key:
        return []
    for pattern, phrase in table.items():
        if pattern in key:
            return [phrase]
    return ["user instruction, verbatim: {}".format(key)]


def diff_words(rows: Sequence[Dict[str, Any]]) -> List[str]:
    """Turn a compare report into 'what still needs to move' wording."""
    words: List[str] = []
    for row in rows or []:
        if row.get("action") != "adjust":
            continue
        dimension = str(row.get("dimension", ""))
        delta = float(row.get("delta", 0.0))
        direction = "more" if delta > 0 else "less"
        short = dimension.split(".", 1)[-1].replace("_", " ")
        words.append("still needs {} {}".format(direction, short))
    return words


def build_prompt(
    profile: Dict[str, Any],
    mode: str = "reference_board",
    intent: str = "",
    diff: Sequence[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    if mode not in MODES:
        raise ValueError("unknown mode: {!r} (expected one of {})".format(mode, ", ".join(MODES)))

    positive: List[str] = []
    positive.extend(lighting_words(profile))
    positive.extend(color_words(profile))
    positive.extend(tone_words(profile))
    positive.extend(texture_words(profile))

    if mode == "background_only":
        positive.append(
            "background only: keep the child, face, hair, hands and clothing exactly as photographed"
        )
        positive.extend(background_words(profile))
    elif mode == "reference_board":
        positive.append("empty scene study, styling reference, no person required")
        positive.extend(background_words(profile))
    else:
        positive.append(
            "same child, same age, same expression, same pose as the source photograph"
        )

    positive.extend(intent_words(intent))
    positive.extend(diff_words(diff))

    negatives: List[str] = []
    negatives.extend(IDENTITY_NEGATIVES)
    negatives.extend(EXPRESSION_NEGATIVES)
    negatives.extend(CHILDHOOD_NEGATIVES)
    negatives.extend(ARTIFACT_NEGATIVES)
    negatives.extend(STRUCTURAL_NEGATIVES)

    return {
        "mode": mode,
        "mode_note": MODE_NOTES[mode],
        "positive": positive,
        "negative": negatives,
        "params": {
            "max_strength": MODE_STRENGTH[mode],
            "denoise_hint": "start at the lowest value that changes the region; raise only if the region is untouched",
            "mask": "child, face, hair, hands, clothing" if mode == "background_only" else "none",
        },
        "verify": [
            "Compare the generated frame against the original: face shape, eye shape, eye spacing, nose, mouth, ears, hairline, expression.",
            "Confirm the child reads as the same age -- no adult contour, no makeup.",
            "Inspect hands at 100%: extra, missing or fused fingers are the most common generative failure.",
            "Re-run: python scripts/style_profile.py compare <result> --profile <profile.json>",
            "Any Identity / Childhood / Expression failure: discard the generation and keep the original.",
        ],
        "privacy": (
            "None -- no photograph is uploaded in reference_board mode."
            if mode == "reference_board"
            else "Sending a photograph of a child to a third-party generation service requires "
            "explicit user consent first (SKILL.md section 15). State it, then wait."
        ),
    }


def render_markdown(result: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Generation prompt ({})".format(result["mode"]))
    lines.append("")
    lines.append("> {}".format(result["mode_note"]))
    lines.append("")
    lines.append("## Positive")
    lines.append("")
    lines.append(", ".join(result["positive"]) + ".")
    lines.append("")
    lines.append("## Negative")
    lines.append("")
    lines.append(", ".join(result["negative"]) + ".")
    lines.append("")
    lines.append("## Params")
    lines.append("")
    for key, value in result["params"].items():
        lines.append("- **{}**: {}".format(key, value))
    lines.append("")
    lines.append("## Verify after generation")
    lines.append("")
    for item in result["verify"]:
        lines.append("- {}".format(item))
    lines.append("")
    lines.append("## Privacy")
    lines.append("")
    lines.append(result["privacy"])
    lines.append("")
    return "\n".join(lines)


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="build_generation_prompt.py",
        description="Compile a learned Style Profile into an image-generation prompt.",
    )
    parser.add_argument("--profile", required=True, help="profile JSON from style_profile.py learn")
    parser.add_argument("--diff", help="compare JSON (list of rows) from style_profile.py compare --json")
    parser.add_argument("--mode", default="reference_board", choices=list(MODES))
    parser.add_argument("--intent", default="", help="short user instruction, e.g. 再暖一点")
    parser.add_argument("--out", help="write the prompt to this path instead of stdout")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    args = parser.parse_args(argv)

    profile = _load_json(args.profile)
    if not isinstance(profile, dict):
        print("error: profile must be a JSON object", file=sys.stderr)
        return 2

    diff = None
    if args.diff:
        diff = _load_json(args.diff)
        if not isinstance(diff, list):
            print("error: diff must be a JSON list of compare rows", file=sys.stderr)
            return 2

    result = build_prompt(profile, mode=args.mode, intent=args.intent, diff=diff)
    text = json.dumps(result, ensure_ascii=False, indent=2) if args.json else render_markdown(result)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
