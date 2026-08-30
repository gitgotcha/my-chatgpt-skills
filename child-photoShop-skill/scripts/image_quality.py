#!/usr/bin/env python3
"""Technical quality scoring for children's photo culling.

    image_quality.py <image_or_folder> [--json] [--csv report.csv]

Scores only the *technical* dimensions.  Expression, story and emotion are
judged by the agent, not by this script -- see
references/photo-culling-guidelines.md for how the two halves combine.

Per-image scores are all 0-1 (higher is better):

    sharpness      Laplacian variance, normalised
    brightness     distance from a bright-studio target luma
    exposure       penalty for clipped highlights and crushed shadows
    clipping       share of usable (non-clipped) pixels
    blur           motion/defocus blur estimate from gradient energy

Dependencies: pillow, numpy.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import Any, Dict, List, Sequence

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style_profile import downscale, load_rgb, to_luma  # noqa: E402

# Children's studio work targets a bright, airy frame, so the ideal mean luma
# sits well above the 0.5 "correct exposure" rule of thumb.
TARGET_LUMA = 0.58

# Sharpness is measured at a higher resolution than the colour statistics:
# downscaling to 1024 smooths away exactly the fine detail that distinguishes
# a focused frame from a defocused one.
ANALYSIS_EDGE = 1024
SHARPNESS_EDGE = 1600

# Calibration constants for the saturating maps below.  A hard
# `score = var / NORM` puts a perfectly sharp photo at 0.02, which is useless.
# `var / (var + K)` saturates gently instead: on the test fixtures a sharp
# frame lands near 0.4 and a defocused one near 0.03, leaving headroom for
# real photographs, which carry far more detail than synthetic gradients.
SHARPNESS_K = 0.0006
BLUR_K = 0.004


def _laplacian(luma: np.ndarray) -> np.ndarray:
    k = np.array([[0.0, 1.0, 0.0], [1.0, -4.0, 1.0], [0.0, 1.0, 0.0]], dtype=np.float32)
    padded = np.pad(luma, 1, mode="reflect")
    out = (
        k[0, 1] * padded[:-2, 1:-1]
        + k[1, 0] * padded[1:-1, :-2]
        + k[1, 1] * padded[1:-1, 1:-1]
        + k[1, 2] * padded[1:-1, 2:]
        + k[2, 1] * padded[2:, 1:-1]
    )
    return out


def score_array(rgb: np.ndarray) -> Dict[str, float]:
    detail = to_luma(downscale(rgb, edge=SHARPNESS_EDGE)).astype(np.float32)
    luma = to_luma(downscale(rgb, edge=ANALYSIS_EDGE)).astype(np.float32)

    # Laplacian variance: the primary focus measure.  Saturating map, see the
    # calibration note above.
    lap_var = float(_laplacian(detail).var())
    sharpness = lap_var / (lap_var + SHARPNESS_K)

    # Mean gradient energy: a secondary, weaker indicator of defocus/motion.
    #
    # This is named `detail`, NOT `blur`, on purpose.  It rises as the image
    # gets sharper.  An earlier field called `blur` carried this same number,
    # and an agent reading `blur=0.58` on a tack-sharp frame would conclude
    # the frame was soft -- exactly backwards.  Names that invert their own
    # meaning are worse than no metric at all.
    grad = float(
        np.abs(np.diff(luma, axis=0)).mean() + np.abs(np.diff(luma, axis=1)).mean()
    )
    detail = grad / (grad + BLUR_K)

    mean = float(luma.mean())
    brightness = float(np.clip(1.0 - abs(mean - TARGET_LUMA) / 0.45, 0.0, 1.0))

    clip_high = float((luma > 0.985).mean())
    clip_low = float((luma < 0.015).mean())
    clipping = float(np.clip(1.0 - (clip_high * 3.0 + clip_low * 3.0), 0.0, 1.0))

    exposure = float(np.clip(
        brightness * 0.5 + clipping * 0.5 - max(0.0, clip_high - 0.02) * 4.0, 0.0, 1.0))

    return {
        "sharpness": round(sharpness, 4),
        "lap_var": round(lap_var, 7),
        "detail": round(detail, 4),
        "brightness": round(brightness, 4),
        "clipping": round(clipping, 4),
        "exposure": round(exposure, 4),
        "mean_luma": round(mean, 4),
        "clip_high": round(clip_high, 5),
        "clip_low": round(clip_low, 5),
    }


def score_image(path: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {"filename": os.path.basename(path), "path": path}
    try:
        result.update(score_array(load_rgb(path)))
    except Exception as exc:  # unreadable files must not abort a batch
        result["error"] = "{}: {}".format(type(exc).__name__, exc)
        for key in ("sharpness", "detail", "brightness", "clipping", "exposure"):
            result[key] = 0.0
    return result


def score_directory(paths: Sequence[str]) -> List[Dict[str, Any]]:
    return [score_image(p) for p in paths]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="image_quality.py", description="Technical quality scoring for culling."
    )
    parser.add_argument("path", help="image file or folder")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--csv", help="write a CSV report")
    args = parser.parse_args(argv)

    from style_profile import collect_images  # noqa: PLC0415

    rows = score_directory(collect_images(args.path))

    if args.csv:
        os.makedirs(os.path.dirname(os.path.abspath(args.csv)), exist_ok=True)
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print("wrote {}".format(args.csv))
        return 0

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    header = "{:<28} {:>9} {:>9} {:>9} {:>9}".format(
        "filename", "sharpness", "exposure", "clipping", "detail")
    print(header)
    print("-" * len(header))
    for r in rows:
        print("{:<28} {:>9.3f} {:>9.3f} {:>9.3f} {:>9.3f}".format(
            r["filename"][:28], r["sharpness"], r["exposure"], r["clipping"], r["detail"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
