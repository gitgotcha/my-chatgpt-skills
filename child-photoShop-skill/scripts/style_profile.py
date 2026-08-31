#!/usr/bin/env python3
"""Style profile learning and comparison for child-photoShop-skill.

Two subcommands:

    learn <image_or_folder> [--name NAME] [--out profile.json]
        Learn a reusable style profile from one or more reference/template
        photos and write it as JSON.

    compare <image> --profile profile.json [--json]
        Report how far a target photo deviates from a learned profile.

Design constraint (identity safety by construction):
    A profile contains ONLY global / regional tonal, colour and texture
    parameters.  It never carries geometry, face shape, pose, hairstyle or
    garment identity.  Therefore applying a profile cannot alter who the
    child is -- the guarantee comes from the data model, not from a prompt.

Dependencies: pillow, numpy (opencv-python optional, unused here).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from typing import Any, Dict, List, Sequence

import numpy as np
from PIL import Image

SCHEMA_VERSION = "1.0"
MAX_STRENGTH_CHILD = 0.85
STAT_EDGE = 1024          # statistics are computed on a downscaled copy
PALETTE_K = 6
PALETTE_SAMPLES = 20000

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp")


# --------------------------------------------------------------------------
# basic image helpers
# --------------------------------------------------------------------------

def load_rgb(path: str) -> np.ndarray:
    """Load an image as a float RGB array in [0, 1]."""
    with Image.open(path) as img:
        img = img.convert("RGB")
        return np.asarray(img, dtype=np.float32) / 255.0


def downscale(rgb: np.ndarray, edge: int = STAT_EDGE) -> np.ndarray:
    """Downscale so the long edge is at most `edge` pixels (no-op if smaller)."""
    h, w = rgb.shape[:2]
    longest = max(h, w)
    if longest <= edge:
        return rgb
    scale = edge / float(longest)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    with Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)) as im:
        im = im.resize((new_w, new_h), Image.LANCZOS)
        return np.asarray(im, dtype=np.float32) / 255.0


def to_luma(rgb: np.ndarray) -> np.ndarray:
    """Rec.709 luminance in [0, 1]."""
    return (
        0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    ).astype(np.float32)


def box_blur(arr: np.ndarray, radius: int = 2) -> np.ndarray:
    """Separable box blur, reflect padding."""
    if radius < 1:
        return arr.copy()
    pad = radius
    a = np.pad(arr, pad, mode="reflect")
    k = 2 * radius + 1
    kernel = np.ones(k, dtype=np.float32) / k
    tmp = np.apply_along_axis(lambda m: np.convolve(m, kernel, mode="valid"), 0, a)
    out = np.apply_along_axis(lambda m: np.convolve(m, kernel, mode="valid"), 1, tmp)
    return out


def skin_mask(rgb: np.ndarray) -> np.ndarray:
    """Skin-coloured pixel rule, broadened for children.

    The classic Kovac RGB rule alone is not selective enough here: after a
    warming pass a beige studio background also satisfies it, which would make
    the mask cover the whole frame and render skin protection useless.  Hue and
    saturation bands keep it in the red-orange skin range.

    It still cannot separate skin from a warm beige background -- they really
    are the same colour.  Callers should therefore treat a large mask as
    "low confidence" rather than as a precise segmentation, and prefer
    asymmetric protection (cap the damage) over blanket damping.
    """
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    hsv = rgb_to_hsv(rgb)
    hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]

    return (
        (r > 0.30) & (g > 0.15) & (b > 0.08)
        & ((mx - mn) > 0.05)
        & (np.abs(r - g) > 0.04)
        & (r > g) & (r > b)
        & ((hue <= 0.14) | (hue >= 0.94))     # ~0-50 degrees, plus red wrap-around
        & (sat > 0.08) & (sat < 0.70)
        & (val > 0.25)
    )


def srgb_to_linear(c: np.ndarray) -> np.ndarray:
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1.0 / 2.4) - 0.055)


def rgb_to_lab(rgb01: np.ndarray) -> np.ndarray:
    """sRGB [0,1] -> CIE Lab (D65).  Accepts a single colour or an array."""
    arr = np.atleast_2d(np.asarray(rgb01, dtype=np.float64).reshape(-1, 3))
    lin = srgb_to_linear(arr)
    m = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ]
    )
    xyz = lin @ m.T
    white = np.array([0.95047, 1.0, 1.08883])
    xyz = xyz / white
    eps = 216.0 / 24389.0
    kappa = 24389.0 / 27.0
    f = np.where(xyz > eps, np.cbrt(xyz), (kappa * xyz + 16.0) / 116.0)
    lab = np.empty_like(f)
    lab[:, 0] = 116.0 * f[:, 1] - 16.0
    lab[:, 1] = 500.0 * (f[:, 0] - f[:, 1])
    lab[:, 2] = 200.0 * (f[:, 1] - f[:, 2])
    # Always (n, 3): callers index [0] for a single colour, so returning a
    # flattened (3,) array for scalar input would silently break them.
    return lab.reshape(-1, 3)


def rgb_to_hex(rgb01: Sequence[float]) -> str:
    r, g, b = (int(round(max(0.0, min(1.0, c)) * 255)) for c in rgb01[:3])
    return "#{:02X}{:02X}{:02X}".format(r, g, b)


# --------------------------------------------------------------------------
# RGB <-> HSV (vectorised, no colour-science dependency)
# --------------------------------------------------------------------------

def rgb_to_hsv(rgb: np.ndarray) -> np.ndarray:
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    df = mx - mn
    h = np.zeros_like(mx)
    nz = df > 1e-8

    idx = nz & (mx == r)
    h[idx] = ((g[idx] - b[idx]) / df[idx]) % 6.0
    idx = nz & (mx == g)
    h[idx] = ((b[idx] - r[idx]) / df[idx]) + 2.0
    idx = nz & (mx == b)
    h[idx] = ((r[idx] - g[idx]) / df[idx]) + 4.0

    h = h / 6.0
    s = np.where(mx > 1e-8, df / np.maximum(mx, 1e-8), 0.0)
    return np.stack([h, s, mx], axis=-1).astype(np.float32)


def hsv_to_rgb(hsv: np.ndarray) -> np.ndarray:
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    i = np.floor(h * 6.0)
    f = h * 6.0 - i
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    i = i.astype(np.int64) % 6

    out = np.zeros(hsv.shape, dtype=np.float32)
    for k, (rr, gg, bb) in enumerate(
        [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)]
    ):
        m = i == k
        out[..., 0][m] = rr[m]
        out[..., 1][m] = gg[m]
        out[..., 2][m] = bb[m]
    return out


# --------------------------------------------------------------------------
# colour palette
# --------------------------------------------------------------------------

def _kmeans(data: np.ndarray, k: int, iters: int = 12, seed: int = 42):
    """Deterministic k-means.  `data` is (n, 3) float in [0, 1]."""
    n = data.shape[0]
    k = min(k, n)
    rng = np.random.default_rng(seed)
    # k-means++-lite: first centre random, then farthest-point seeding
    centres = np.empty((k, 3), dtype=np.float64)
    centres[0] = data[rng.integers(n)]
    closest = ((data - centres[0]) ** 2).sum(axis=1)
    for i in range(1, k):
        total = closest.sum()
        if total <= 1e-12:
            centres[i] = data[rng.integers(n)]
        else:
            centres[i] = data[int(np.argmax(closest / total * rng.random(n)))]
        d = ((data - centres[i]) ** 2).sum(axis=1)
        closest = np.minimum(closest, d)

    labels = np.zeros(n, dtype=np.int64)
    for _ in range(iters):
        dist = ((data[:, None, :] - centres[None, :, :]) ** 2).sum(axis=2)
        new_labels = dist.argmin(axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for j in range(k):
            members = data[labels == j]
            if len(members):
                centres[j] = members.mean(axis=0)

    counts = np.bincount(labels, minlength=k).astype(np.float64)
    weights = counts / max(counts.sum(), 1.0)
    return centres, weights


def extract_palette(rgb: np.ndarray, k: int = PALETTE_K) -> List[Dict[str, Any]]:
    flat = rgb.reshape(-1, 3).astype(np.float64)
    if flat.shape[0] > PALETTE_SAMPLES:
        idx = np.linspace(0, flat.shape[0] - 1, PALETTE_SAMPLES).astype(np.int64)
        flat = flat[idx]

    centres, weights = _kmeans(flat, k)
    order = np.argsort(-weights)

    palette = []
    for j in order:
        if weights[j] < 1e-4:
            continue
        colour = np.clip(centres[j], 0.0, 1.0)
        lab = rgb_to_lab(colour)[0]
        palette.append(
            {
                "hex": rgb_to_hex(colour),
                "weight": round(float(weights[j]), 4),
                "lab": [round(float(x), 2) for x in lab],
            }
        )
    return palette


# --------------------------------------------------------------------------
# profile computation
# --------------------------------------------------------------------------

def gray_world_gains(rgb: np.ndarray) -> Dict[str, float]:
    """Gray-world white balance gains; g is the reference channel.

    These are NEUTRALISING gains: multiplying the image by them makes it
    neutral, so they are the inverse of the image's cast.  A warm photo gets
    r_gain < 1 and b_gain > 1.  See `_temperature_hint` and
    `apply_style.apply_white_balance` for the two places this matters.
    """
    means = rgb.reshape(-1, 3).mean(axis=0).astype(np.float64)
    r_mean, g_mean, b_mean = [max(float(m), 1e-6) for m in means]
    return {
        "r_gain": round(g_mean / r_mean, 4),
        "g_gain": 1.0,
        "b_gain": round(g_mean / b_mean, 4),
    }


def _temperature_hint(r_gain: float, b_gain: float) -> str:
    """Classify the *look* of the image from its gray-world gains.

    A gray-world gain is the correction that would NEUTRALISE the image, so it
    is the inverse of the look: a warm photo has r_gain < 1 (its red channel
    must be reduced) and b_gain > 1 (its blue must be lifted).  Warmth is
    therefore b_gain - r_gain, not the other way round.

    image = neutral / gain   =>   gain high  <=>  channel low in the image
    """
    warmth = b_gain - r_gain
    if warmth > 0.12:
        return "warm"
    if warmth < -0.12:
        return "cool"
    return "neutral"


def _light_direction(luma: np.ndarray) -> str:
    h, w = luma.shape
    top = float(luma[: h // 3, :].mean())
    bottom = float(luma[-(h // 3):, :].mean())
    left = float(luma[:, : w // 3].mean())
    right = float(luma[:, -(w // 3):].mean())
    vert = top - bottom
    horiz = left - right
    parts = []
    if abs(vert) > 0.02:
        parts.append("top" if vert > 0 else "bottom")
    if abs(horiz) > 0.02:
        parts.append("left" if horiz > 0 else "right")
    if not parts:
        return "even"
    return "front-" + "-".join(parts) if len(parts) == 1 else "-".join(parts)


def compute_profile(paths: Sequence[str], name: str = "style", role: str = "color") -> Dict[str, Any]:
    """Compute a style profile from one or more reference images.

    With several references each dimension takes the median, and the spread is
    reported so the caller can warn about inconsistent references.
    """
    per_image = []
    for p in paths:
        rgb = downscale(load_rgb(p))
        per_image.append(_single_profile(rgb))

    if len(per_image) == 1:
        merged = dict(per_image[0])
        variances: Dict[str, float] = {}
    else:
        merged, variances = _merge_profiles(per_image)

    merged["schemaVersion"] = SCHEMA_VERSION
    merged["name"] = name
    merged["learned_at"] = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    merged["source"] = {
        "references": [os.path.basename(p) for p in paths],
        "role": role,
        "generator": "child-photoShop-skill/style_profile.py",
    }
    if variances:
        merged["source"]["dimension_variance"] = variances
    merged["constraints"] = {
        "identity_lock": True,
        "childhood_preservation": True,
        "expression_preservation": True,
        "max_strength": MAX_STRENGTH_CHILD,
    }
    return merged


def _single_profile(rgb: np.ndarray) -> Dict[str, Any]:
    luma = to_luma(rgb)
    flat = luma.reshape(-1)
    p_low = float(np.percentile(flat, 10))
    p_high = float(np.percentile(flat, 90))

    shadow_lift = float(flat[flat <= p_low].mean()) if np.any(flat <= p_low) else p_low
    highlight_top = flat[flat >= p_high]
    highlight_rolloff = float(highlight_top.mean()) if highlight_top.size else p_high
    clip_high = float((flat > 0.985).mean())
    clip_low = float((flat < 0.015).mean())

    hsv = rgb_to_hsv(rgb)
    sat = hsv[..., 1]
    mean_saturation = float(sat.reshape(-1).mean())

    # dominant hues: 36 bins of 10 degrees, keep the strongest few
    hue_hist, _ = np.histogram(hsv[..., 0].reshape(-1), bins=36, range=(0.0, 1.0))
    top_bins = np.argsort(-hue_hist)[:3]
    dominant_hues = [int(round(b * 10)) for b in sorted(top_bins.tolist())]

    gains = gray_world_gains(rgb)

    # skin tone
    smask = skin_mask(rgb)
    if smask.sum() > 32:
        skin_rgb = rgb[smask].mean(axis=0)
        skin_luma = float(to_luma(rgb)[smask].mean())
        skin_sat = float(rgb_to_hsv(rgb)[..., 1][smask].mean())
    else:
        skin_rgb = np.array([0.91, 0.77, 0.63], dtype=np.float32)
        skin_luma = 0.74
        skin_sat = 0.30
    skin_lab = rgb_to_lab(skin_rgb)[0]

    # background ring: outer 15% border
    h, w = luma.shape
    bh, bw = max(1, int(h * 0.15)), max(1, int(w * 0.15))
    ring = np.ones((h, w), dtype=bool)
    ring[bh:-bh, bw:-bw] = False
    bg_rgb = rgb[ring].mean(axis=0)

    # texture
    blurred = box_blur(luma, radius=2)
    residual = luma - blurred
    grain = float(residual.reshape(-1).std())
    microcontrast = float(np.abs(residual).reshape(-1).mean())
    hl = luma > 0.85
    halation = float(max(0.0, (blurred[hl] - luma[hl]).mean())) if hl.any() else 0.0

    # lighting
    grad = float(np.abs(np.diff(luma, axis=1)).mean() + np.abs(np.diff(luma, axis=0)).mean())
    softness = float(1.0 / (1.0 + 12.0 * grad))

    return {
        "exposure": {
            "mean_luma": round(float(flat.mean()), 4),
            "median_luma": round(float(np.median(flat)), 4),
            "contrast": round(float(flat.std()), 4),
            "shadow_lift": round(shadow_lift, 4),
            "highlight_rolloff": round(highlight_rolloff, 4),
            "clip_high": round(clip_high, 5),
            "clip_low": round(clip_low, 5),
        },
        "white_balance": {
            **gains,
            "temperature_hint": _temperature_hint(gains["r_gain"], gains["b_gain"]),
        },
        "color": {
            "mean_saturation": round(mean_saturation, 4),
            "dominant_hues": dominant_hues,
            "palette": extract_palette(rgb),
        },
        "skin": {
            "tone_hex": rgb_to_hex(skin_rgb),
            "target_luma": round(skin_luma, 4),
            "warmth": round(float(skin_lab[1]), 3),
            "saturation": round(skin_sat, 4),
            "coverage": round(float(smask.mean()), 4),
        },
        "background": {
            "tone_hex": rgb_to_hex(bg_rgb),
            "saturation_bias": 0.0,
            "vignette": round(float(max(0.0, luma.mean() - luma[ring].mean()) * 0.5), 4),
        },
        "lighting": {
            "direction": _light_direction(luma),
            "softness": round(softness, 4),
            "shadow_depth": round(float(max(0.0, flat.mean() - shadow_lift)), 4),
        },
        "texture": {
            "grain": round(min(grain, 1.0), 4),
            "microcontrast": round(min(microcontrast * 4.0, 1.0), 4),
            "halation": round(min(halation * 3.0, 1.0), 4),
        },
        "mood": [],
    }


_NUMERIC_DIMS = (
    ("exposure", "mean_luma"),
    ("exposure", "median_luma"),
    ("exposure", "contrast"),
    ("exposure", "shadow_lift"),
    ("exposure", "highlight_rolloff"),
    ("white_balance", "r_gain"),
    ("white_balance", "b_gain"),
    ("color", "mean_saturation"),
    ("skin", "target_luma"),
    ("skin", "warmth"),
    ("background", "vignette"),
    ("lighting", "softness"),
    ("lighting", "shadow_depth"),
    ("texture", "grain"),
    ("texture", "microcontrast"),
    ("texture", "halation"),
)

# Skin dimensions are only trustworthy when the mask is selective, on BOTH
# sides.  A mask that covers most of a frame has matched the background as
# well -- warm beige is the same colour as skin -- so its mean colour says
# nothing about the child.  Comparing one frame's 100%-coverage mask against
# another's 86%-coverage mask produces a large, confident, meaningless delta
# that then tells the agent to warm the skin that just got warmer.
SKIN_DIMS = frozenset({("skin", "target_luma"), ("skin", "warmth")})

# Outside this band the mask carries no information either way.
SKIN_COVERAGE_MIN = 0.002
SKIN_COVERAGE_MAX = 0.6


def _merge_profiles(profiles: List[Dict[str, Any]]):
    merged = json.loads(json.dumps(profiles[0]))
    variances: Dict[str, float] = {}
    for section, key in _NUMERIC_DIMS:
        values = [p[section][key] for p in profiles]
        merged[section][key] = round(float(np.median(values)), 4)
        variances["{}.{}".format(section, key)] = round(float(np.std(values)), 4)
    # categorical fields and the palette follow the first (primary) reference
    return merged, variances


# --------------------------------------------------------------------------
# comparison
# --------------------------------------------------------------------------

# Per-dimension "is this worth touching?" thresholds.
#
# A single absolute threshold cannot work across dimensions whose units differ
# by two orders of magnitude: 0.25 in normalised luminance is about a stop,
# while 0.25 in Lab a* (skin warmth) is invisible noise.  These are the
# smallest deltas a viewer would actually notice.
COMPARE_THRESHOLDS: Dict[str, float] = {
    "exposure.mean_luma": 0.08,
    "exposure.median_luma": 0.08,
    "exposure.contrast": 0.05,
    "exposure.shadow_lift": 0.08,
    "exposure.highlight_rolloff": 0.08,
    "white_balance.r_gain": 0.06,
    "white_balance.b_gain": 0.06,
    "color.mean_saturation": 0.08,
    "skin.target_luma": 0.05,
    "skin.warmth": 3.0,          # Lab a*, roughly -20..30
    "background.vignette": 0.05,
    "lighting.softness": 0.10,
    "lighting.shadow_depth": 0.08,
    "texture.grain": 0.02,
    "texture.microcontrast": 0.02,
    "texture.halation": 0.05,
}
DEFAULT_COMPARE_THRESHOLD = 0.08


def threshold_for(dimension: str) -> float:
    return COMPARE_THRESHOLDS.get(dimension, DEFAULT_COMPARE_THRESHOLD)


def compare_profile(target_path: str, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Compare a target image against a learned profile dimension by dimension."""
    rgb = downscale(load_rgb(target_path))
    current = _single_profile(rgb)

    # Reliability gate for the skin dimensions -- see SKIN_DIMS above.
    skin_reliable = all(
        SKIN_COVERAGE_MIN < float(side.get("skin", {}).get("coverage", 0.0)) < SKIN_COVERAGE_MAX
        for side in (current, profile)
    )

    rows = []
    for section, key in _NUMERIC_DIMS:
        dimension = "{}.{}".format(section, key)
        prof_val = float(profile.get(section, {}).get(key, 0.0))
        cur_val = float(current[section][key])
        delta = round(prof_val - cur_val, 4)

        if (section, key) in SKIN_DIMS and not skin_reliable:
            action, note = "skip", "unreliable: skin mask is not selective"
        else:
            action = "skip" if abs(delta) < threshold_for(dimension) else "adjust"
            note = None

        rows.append(
            {
                "dimension": dimension,
                "target": cur_val,
                "profile": prof_val,
                "delta": delta,
                "threshold": threshold_for(dimension),
                "action": action,
                "note": note,
            }
        )
    return rows


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def collect_images(path: str) -> List[str]:
    if os.path.isfile(path):
        return [path]
    if not os.path.isdir(path):
        raise SystemExit("path not found: {}".format(path))
    files = [
        os.path.join(path, f)
        for f in sorted(os.listdir(path))
        if f.lower().endswith(IMAGE_EXT)
    ]
    if not files:
        raise SystemExit("no supported images found in: {}".format(path))
    return files


def _cmd_learn(args: argparse.Namespace) -> int:
    paths = collect_images(args.path)
    profile = compute_profile(paths, name=args.name, role=args.role)

    text = json.dumps(profile, ensure_ascii=False, indent=2)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print("learned style profile from {} image(s) -> {}".format(len(paths), args.out))
    else:
        print(text)

    variances = profile.get("source", {}).get("dimension_variance", {})
    inconsistent = {k: v for k, v in variances.items() if v > 0.15}
    if inconsistent:
        print(
            "\nWARNING: references disagree on {} dimension(s): {}".format(
                len(inconsistent), ", ".join(sorted(inconsistent))
            ),
            file=sys.stderr,
        )
        print("Specify a single primary reference before applying.", file=sys.stderr)
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    with open(args.profile, "r", encoding="utf-8") as fh:
        profile = json.load(fh)
    rows = compare_profile(args.image, profile)

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    print("{:<32} {:>9} {:>9} {:>9}  {}".format("dimension", "target", "profile", "delta", "action"))
    print("-" * 74)
    for r in rows:
        label = "{}*".format(r["action"]) if r.get("note") else r["action"]
        print(
            "{:<32} {:>9.4f} {:>9.4f} {:>9.4f}  {}".format(
                r["dimension"], r["target"], r["profile"], r["delta"], label
            )
        )
    ignored = [r["dimension"] for r in rows if r.get("note")]
    if ignored:
        print("\n* ignored ({}): a skin mask that covers most of the frame has".format(
            ", ".join(ignored)))
        print("  matched the background too, so these numbers compare different")
        print("  pixel populations and would send the grade the wrong way.")
    adjustments = [r for r in rows if r["action"] == "adjust"]
    print("\n{} of {} dimensions exceed their threshold and need adjustment:".format(
        len(adjustments), len(rows)))
    for r in adjustments:
        print("  {:<32} delta={:+.4f} (threshold {})".format(
            r["dimension"], r["delta"], r["threshold"]))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="style_profile.py",
        description="Learn or compare children's photography style profiles.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_learn = sub.add_parser("learn", help="learn a style profile from reference image(s)")
    p_learn.add_argument("path", help="reference image file or folder")
    p_learn.add_argument("--name", default="style", help="profile name")
    p_learn.add_argument(
        "--role",
        default="color",
        choices=["color", "lighting", "texture", "composition", "degree", "target"],
        help="reference role; limits what may be transferred",
    )
    p_learn.add_argument("--out", help="write profile JSON to this path")
    p_learn.set_defaults(func=_cmd_learn)

    p_cmp = sub.add_parser("compare", help="compare a photo against a learned profile")
    p_cmp.add_argument("image", help="target image")
    p_cmp.add_argument("--profile", required=True, help="profile JSON path")
    p_cmp.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    p_cmp.set_defaults(func=_cmd_compare)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
