#!/usr/bin/env python3
"""Apply a learned style profile to children's photos.

    apply_style.py <input> --profile profile.json [--strength 0.8]
                   [--out edited/] [--role color] [--manifest manifest.json]

Identity safety by construction
-------------------------------
Every operation here is a per-pixel tonal or colour mapping.  There is no
geometric transform, no face detection, no generative repaint.  A profile
therefore cannot change who the child is -- the guarantee is structural, not
promptry.

The transform chain (fixed order):

    1. white balance gains
    2. luminance tone map (exposure -> contrast -> shadows -> highlights)
    3. saturation, with skin protection
    4. vignette
    5. grain and micro-contrast

Dependencies: pillow, numpy.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from style_profile import (  # noqa: E402
    MAX_STRENGTH_CHILD,
    collect_images,
    compare_profile,
    hsv_to_rgb,
    linear_to_srgb,
    load_rgb,
    rgb_to_hsv,
    skin_mask,
    srgb_to_linear,
    threshold_for,
    to_luma,
)

DEFAULT_STRENGTH = 0.8
JPEG_QUALITY = 95

# which transform steps each reference role is allowed to transfer
ROLE_STEPS: Dict[str, Tuple[str, ...]] = {
    "color": ("white_balance", "saturation", "vignette", "tone"),
    "lighting": ("tone",),
    "texture": ("texture",),
    "composition": (),          # composition is a framing decision, not a filter
    "degree": ("tone", "saturation"),
    "target": ("white_balance", "tone", "saturation", "vignette", "texture"),
}


# --------------------------------------------------------------------------
# individual transforms
# --------------------------------------------------------------------------

def exposure_curve(luma: np.ndarray, gain: float) -> np.ndarray:
    """A shoulder tone curve: `1 - exp(-gain * linear_luma)`.

    A plain gamma (`luma ** g`) is the obvious way to hit a target mean, but
    raising exposure with it drives highlights straight into clipping -- on a
    children's frame that means blown-out skin and featureless white clothing.
    This curve rises monotonically and asymptotes at 1.0, so highlights roll
    off instead of clipping.  Measured clipping on the test fixture drops from
    ~8% of pixels (gamma) to ~0% (this curve) for the same target mean.
    """
    lin = srgb_to_linear(np.clip(luma, 0.0, 1.0))
    return np.clip(linear_to_srgb(1.0 - np.exp(-gain * lin)), 0.0, 1.0)


def _solve_exposure_gain(luma: np.ndarray, target_mean: float) -> float:
    """Bisect the shoulder-curve gain so the mean lands on `target_mean`."""
    lo, hi = 0.05, 24.0
    for _ in range(48):
        mid = (lo + hi) / 2.0
        if float(exposure_curve(luma, mid).mean()) < target_mean:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-4:
            break
    return (lo + hi) / 2.0


def apply_white_balance(
    rgb: np.ndarray, source: Dict[str, Any], profile: Dict[str, Any], strength: float
) -> np.ndarray:
    """Move the source's cast onto the profile's cast.

    The gray-world gains in both dicts are NEUTRALISING gains, i.e.
    `image = neutral / gain`.  To make the source look like the reference:

        source * X = reference
        (neutral / s) * X = neutral / d
        X = s / d

    Note the direction: it is source-over-destination, not the other way
    round.  Inverting it would push a cool photo even cooler.

    Gains above 1 can push a bright channel past white.  A hard clip there
    would flatten skin and clothing, so the top end gets a soft shoulder
    instead -- it asymptotes at 1.0 and stays monotone.
    """
    src_gains = source["white_balance"]
    dst_gains = profile.get("white_balance", {})
    out = rgb.copy()
    for i, key in enumerate(("r_gain", "g_gain", "b_gain")):
        s = max(float(src_gains.get(key, 1.0)), 1e-6)
        d = max(float(dst_gains.get(key, 1.0)), 1e-6)
        factor = 1.0 + (s / d - 1.0) * strength
        out[..., i] = soft_clip_highlights(out[..., i] * factor)
    return out


def soft_clip_highlights(x: np.ndarray, knee: float = 0.85) -> np.ndarray:
    """Roll highlights off toward 1.0 instead of clipping them flat."""
    span = 1.0 - knee
    return np.where(
        x <= knee,
        x,
        knee + span * (1.0 - np.exp(-(x - knee) / span)),
    ).astype(np.float32)


def build_tone_lut(
    source_luma: np.ndarray,
    target_mean: float,
    target_contrast: float,
    target_shadow: float,
    target_high: float,
    strength: float,
    size: int = 256,
) -> Tuple[np.ndarray, np.ndarray]:
    """Build a monotone, bounded tone curve: exposure -> contrast -> shadows -> highlights.

    Why a LUT instead of pixel arithmetic
    -------------------------------------
    Scaling channels by a luminance ratio (the obvious implementation) pushes
    the strongest channel past 1.0 and blows the highlights -- on a children's
    frame that means featureless white clothing and destroyed skin detail.
    Composing the steps into a single curve, then forcing the curve to stay
    within [0,1] and to remain monotone, makes clipping impossible by
    construction instead of by luck.

    Endpoints are pinned to 0 and 1 so the black and white points survive:
    a low-contrast children's look must stay low-contrast, not turn milky.
    """
    x = np.linspace(0.0, 1.0, size, dtype=np.float32)
    y = x.copy()

    # 1. exposure, skipped when the frame is already close enough
    if abs(target_mean - float(source_luma.mean())) > 0.02:
        gain = _solve_exposure_gain(source_luma, target_mean)
        y = exposure_curve(x, gain)

    # 2. contrast about the mean of the tone-mapped distribution
    mapped = np.interp(source_luma.reshape(-1), x, y).astype(np.float32)
    cur_std = float(mapped.std())
    if cur_std > 1e-6:
        k = 1.0 + (target_contrast / cur_std - 1.0) * strength
        mean_now = float(mapped.mean())
        y = mean_now + (y - mean_now) * k

    # 3. shadow lift, weighted toward the darkest region
    mapped = np.interp(source_luma.reshape(-1), x, np.clip(y, 0, 1)).astype(np.float32)
    cur_shadow = float(mapped[mapped <= np.percentile(mapped, 10)].mean())
    lift = (target_shadow - cur_shadow) * strength
    if abs(lift) > 1e-4:
        y = y + lift * np.clip(1.0 - x / 0.35, 0.0, 1.0) ** 2

    # 4. highlight roll-off, weighted toward the brightest region
    mapped = np.interp(source_luma.reshape(-1), x, np.clip(y, 0, 1)).astype(np.float32)
    cur_high = float(mapped[mapped >= np.percentile(mapped, 90)].mean())
    shift = (target_high - cur_high) * strength
    if abs(shift) > 1e-4:
        y = y + shift * np.clip((x - 0.65) / 0.35, 0.0, 1.0) ** 2

    # 5. keep it a legal curve: bounded, monotone, endpoints pinned
    y = np.clip(y, 0.0, 1.0)
    y = np.maximum.accumulate(y)
    y[0], y[-1] = 0.0, 1.0

    # 6. blend toward identity by strength, then re-check the invariants
    y = x + (y - x) * strength
    y = np.clip(y, 0.0, 1.0)
    y = np.maximum.accumulate(y)
    return x, y


def apply_tone(
    rgb: np.ndarray, source: Dict[str, Any], profile: Dict[str, Any], strength: float
) -> np.ndarray:
    """Apply the tone curve. Per channel, which is what a real curves tool does."""
    src_exp = source["exposure"]
    dst_exp = profile.get("exposure", {})
    x, lut = build_tone_lut(
        to_luma(rgb).astype(np.float32),
        target_mean=float(dst_exp.get("mean_luma", src_exp["mean_luma"])),
        target_contrast=float(dst_exp.get("contrast", src_exp["contrast"])),
        target_shadow=float(dst_exp.get("shadow_lift", src_exp["shadow_lift"])),
        target_high=float(dst_exp.get("highlight_rolloff", src_exp["highlight_rolloff"])),
        strength=strength,
    )

    out = np.empty_like(rgb)
    for c in range(rgb.shape[2]):
        out[..., c] = np.interp(rgb[..., c], x, lut)
    return out.astype(np.float32)


def apply_saturation(
    rgb: np.ndarray,
    source: Dict[str, Any],
    profile: Dict[str, Any],
    strength: float,
    skin: np.ndarray | None = None,
) -> np.ndarray:
    """Scale saturation toward the profile, with a skin guard.

    Children's skin is the first thing a parent notices and the easiest thing
    to ruin: "先保证肤色真实，再谈风格".  The guard is a CAP, not a blanket
    damping -- skin saturation may rise toward the reference, but never past
    the reference's own skin saturation by more than 15%.

    An earlier version halved the saturation change on every skin pixel.  That
    backfires: once a warming pass has run, a beige studio background also
    matches the skin rule, the mask covers the whole frame, and the intended
    boost is halved everywhere -- the result never converges on the template.
    A cap degrades gracefully instead.

    The step moves saturation a fraction `strength` of the way to the
    template rather than scaling by a clipped ratio.  A ratio cap of 2.0
    looked like a safety limit but silently made the template unreachable:
    white balance runs first and, on a cool frame, the cast it removes *is*
    most of the colour -- measured saturation dropped 0.31 -> 0.14 on the
    fixture, and a 2x cap cannot climb back to the template's 0.44.  Blending
    toward the target hits it exactly at full strength; the ceiling below is
    what actually stops garish output.
    """
    src_sat = max(float(source["color"]["mean_saturation"]), 1e-4)
    dst_sat = max(float(profile.get("color", {}).get("mean_saturation", src_sat)), 1e-4)

    target_sat = src_sat + (dst_sat - src_sat) * float(np.clip(strength, 0.0, 1.0))
    target_sat = min(max(target_sat, 0.0), dst_sat * 1.25)
    ratio = target_sat / src_sat

    hsv = rgb_to_hsv(rgb)
    hsv[..., 1] = np.clip(hsv[..., 1] * ratio, 0.0, 1.0)

    ref_skin_sat = profile.get("skin", {}).get("saturation")
    if skin is not None and ref_skin_sat is not None:
        coverage = float(skin.mean())
        # A mask covering most of the frame means the rule matched the
        # background too, so it carries no information -- skip the guard
        # rather than clamp the entire image to skin levels.
        if 0.002 < coverage < 0.6:
            cap = min(1.0, float(ref_skin_sat) * 1.15)
            hsv[..., 1] = np.where(skin > 0.5, np.minimum(hsv[..., 1], cap), hsv[..., 1])

    return np.clip(hsv_to_rgb(hsv), 0.0, 1.0).astype(np.float32)


def apply_vignette(rgb: np.ndarray, profile: Dict[str, Any], strength: float) -> np.ndarray:
    amount = float(profile.get("background", {}).get("vignette", 0.0)) * strength
    if amount <= 1e-4:
        return rgb
    h, w = rgb.shape[:2]
    yy = np.linspace(-1.0, 1.0, h, dtype=np.float32)[:, None]
    xx = np.linspace(-1.0, 1.0, w, dtype=np.float32)[None, :]
    r2 = np.clip(xx * xx + yy * yy, 0.0, 2.0)
    falloff = 1.0 - amount * r2
    return np.clip(rgb * falloff[..., None], 0.0, 1.0).astype(np.float32)


def apply_texture(rgb: np.ndarray, profile: Dict[str, Any], strength: float) -> np.ndarray:
    tex = profile.get("texture", {})
    grain = float(tex.get("grain", 0.0)) * strength
    micro = float(tex.get("microcontrast", 0.0)) * strength

    out = rgb
    if micro > 1e-4:
        pil = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))
        blurred = np.asarray(
            pil.filter(ImageFilter.GaussianBlur(radius=3)), dtype=np.float32
        ) / 255.0
        # amount scaled to 0-1 range; 0.5 keeps the effect subtle
        out = np.clip(out + (out - blurred) * micro * 0.5, 0.0, 1.0)

    if grain > 1e-4:
        rng = np.random.default_rng(7)  # deterministic: reruns reproduce the output
        noise = rng.normal(0.0, 1.0, out.shape).astype(np.float32)
        out = np.clip(out + noise * grain * 0.12, 0.0, 1.0)

    return out.astype(np.float32)


# --------------------------------------------------------------------------
# orchestration
# --------------------------------------------------------------------------

def apply_style(
    rgb: np.ndarray,
    profile: Dict[str, Any],
    strength: float = DEFAULT_STRENGTH,
    role: str = "color",
) -> np.ndarray:
    """Apply a style profile to an RGB float array in [0, 1]."""
    max_strength = float(
        profile.get("constraints", {}).get("max_strength", MAX_STRENGTH_CHILD)
    )
    strength = float(np.clip(strength, 0.0, max_strength))

    steps = ROLE_STEPS.get(role)
    if steps is None:
        raise ValueError("unknown role: {}".format(role))
    if not steps:
        return rgb  # composition roles are advisory only

    # The skin mask comes from the ORIGINAL image: after a warming pass a
    # beige background is the same colour as skin, and the mask would swallow
    # the frame.
    skin = skin_mask(rgb).astype(np.float32)

    # Every other measurement is taken live, on the array each step is handed.
    # Feeding every step the *input* image's statistics instead makes them
    # compensate for a state that no longer exists -- warming and tone mapping
    # both raise saturation, so a saturation step working from stale numbers
    # overshoots the template, and a second iteration round overshoots again.
    #
    # The gate below is the minimum edit principle (SKILL.md §十二): a
    # dimension already inside tolerance is left alone.  Re-grading an image
    # that already matches the template is how an iteration round makes the
    # result worse than the round before it.
    out = rgb.astype(np.float32)
    if "white_balance" in steps and _needs(out, profile, "white_balance"):
        out = apply_white_balance(out, _live_stats(out), profile, strength)
    if "tone" in steps and _needs(out, profile, "tone"):
        out = apply_tone(out, _live_stats(out), profile, strength)
    if "saturation" in steps and _needs(out, profile, "saturation"):
        out = apply_saturation(out, _live_stats(out), profile, strength, skin=skin)
    if "vignette" in steps:
        out = apply_vignette(out, profile, strength)
    if "texture" in steps:
        out = apply_texture(out, profile, strength)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def _needs(rgb: np.ndarray, profile: Dict[str, Any], step: str) -> bool:
    """Does `step` have anything to do, measured on the array it would change?

    The gate has to be evaluated per step, on the current array, because the
    steps are coupled: a tone curve that lifts the mids also raises measured
    saturation.  Judging every step up front, against the input image, lets
    saturation drift away from the template round after round while the
    saturation step sits idle because it looked fine before the tone ran.
    """
    live = _live_stats(rgb)
    src_exp = live["exposure"]
    dst_exp = profile.get("exposure", {})
    src_wb = live["white_balance"]
    dst_wb = profile.get("white_balance", {})
    src_sat = live["color"]["mean_saturation"]
    dst_sat = float(profile.get("color", {}).get("mean_saturation", src_sat))

    if step == "tone":
        return any(
            abs(float(dst_exp.get(key, src_exp[key])) - src_exp[key])
            >= threshold_for("exposure." + key)
            for key in ("mean_luma", "contrast", "shadow_lift", "highlight_rolloff")
        )
    if step == "white_balance":
        return any(
            abs(float(dst_wb.get(key, src_wb[key])) - src_wb[key])
            >= threshold_for("white_balance." + key)
            for key in ("r_gain", "b_gain")
        )
    if step == "saturation":
        return abs(dst_sat - src_sat) >= threshold_for("color.mean_saturation")
    raise ValueError("unknown step: {}".format(step))


def _live_stats(rgb: np.ndarray) -> Dict[str, Any]:
    """Measure `rgb` as it is right now, on the same downscaled basis.

    Deliberately cheaper than `_single_profile`: no palette extraction.  This
    runs once per step, and the steps only need exposure, cast and saturation.
    """
    from style_profile import downscale, gray_world_gains, rgb_to_hsv, to_luma  # noqa: PLC0415

    small = downscale(rgb)
    luma = to_luma(small).reshape(-1)
    sat = rgb_to_hsv(small)[..., 1].reshape(-1)
    return {
        "exposure": {
            "mean_luma": float(luma.mean()),
            "contrast": float(luma.std()),
            "shadow_lift": float(luma[luma <= np.percentile(luma, 10)].mean()),
            "highlight_rolloff": float(luma[luma >= np.percentile(luma, 90)].mean()),
        },
        "white_balance": gray_world_gains(small),
        "color": {"mean_saturation": float(sat.mean())},
    }


def append_manifest(path: str, record: Dict[str, Any]) -> None:
    data: Dict[str, Any] = {"records": []}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                data = loaded
                data.setdefault("records", [])
        except (OSError, ValueError):
            pass
    data["records"].append(record)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def process_file(
    path: str,
    profile: Dict[str, Any],
    strength: float,
    role: str,
    out_dir: str,
    manifest: str | None = None,
) -> str:
    rgb = load_rgb(path)
    result = apply_style(rgb, profile, strength=strength, role=role)

    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(path))[0]
    out_path = os.path.join(out_dir, stem + "_styled.jpg")

    img = Image.fromarray((np.clip(result, 0, 1) * 255).astype(np.uint8))
    try:
        with Image.open(path) as src:
            exif = src.getexif()
        if exif:
            img.save(out_path, quality=JPEG_QUALITY, exif=exif)
        else:
            img.save(out_path, quality=JPEG_QUALITY)
    except Exception:
        img.save(out_path, quality=JPEG_QUALITY)

    if manifest:
        append_manifest(
            manifest,
            {
                "action": "apply_style",
                "source": os.path.basename(path),
                "output": out_path,
                "profile": profile.get("name", "style"),
                "role": role,
                "strength": strength,
                "at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                "original_preserved": True,
            },
        )
    return out_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="apply_style.py",
        description="Apply a learned children's photography style profile.",
    )
    parser.add_argument("input", help="image file or folder")
    parser.add_argument("--profile", required=True, help="profile JSON path")
    parser.add_argument("--strength", type=float, default=DEFAULT_STRENGTH,
                        help="0-1, default 0.8 (clamped to the profile's max)")
    parser.add_argument("--out", default="edited", help="output directory")
    parser.add_argument("--role", default="color", choices=sorted(ROLE_STEPS),
                        help="reference role; defaults to the role stored in the profile")
    parser.add_argument("--manifest", help="append a run record to this manifest JSON")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the deviation report and exit without editing")
    args = parser.parse_args(argv)

    with open(args.profile, "r", encoding="utf-8") as fh:
        profile = json.load(fh)

    role = profile.get("source", {}).get("role", args.role)
    files = collect_images(args.input)

    if args.dry_run:
        for f in files:
            rows = compare_profile(f, profile)
            todo = [r for r in rows if r["action"] == "adjust"]
            print("{}: {}/{} dimensions need adjustment".format(
                os.path.basename(f), len(todo), len(rows)))
            for r in todo:
                print("  {:<32} delta={:+.4f}".format(r["dimension"], r["delta"]))
        return 0

    written: List[str] = []
    for f in files:
        written.append(
            process_file(f, profile, args.strength, role, args.out, args.manifest)
        )
    print("applied style to {} image(s) -> {}/".format(len(written), args.out))
    for p in written:
        print("  " + p)
    print("originals untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
