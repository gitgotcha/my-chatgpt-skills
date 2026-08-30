#!/usr/bin/env python3
"""Read the deterministic, boring facts about a photo.

    analyze_image.py <image_or_folder> [--json]

Reports dimensions, orientation, EXIF capture fields, embedded ICC profile,
colour-space guess and a compact luminance histogram.  Deliberately does NOT
guess at aesthetics -- that is the agent's job.  This script exists because
reading EXIF and ICC reliably is something an agent should not re-derive every
time.

Dependencies: pillow, numpy.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Sequence

import numpy as np
from PIL import Image, ExifTags

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style_profile import collect_images, load_rgb, to_luma  # noqa: E402

EXIF_KEYS = {
    "DateTimeOriginal": "captured_at",
    "Make": "camera_make",
    "Model": "camera_model",
    "LensModel": "lens",
    "FNumber": "aperture",
    "ExposureTime": "shutter",
    "ISOSpeedRatings": "iso",
    "FocalLength": "focal_length",
    "Orientation": "orientation",
}

HIST_BINS = 10


def _rational_to_float(value: Any) -> Any:
    try:
        if isinstance(value, tuple) and len(value) == 2:
            num, den = value
            return round(float(num) / float(den), 4) if den else None
        return float(value)
    except (TypeError, ValueError):
        return value


def read_exif(path: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    try:
        with Image.open(path) as img:
            raw = img.getexif()
    except Exception:
        return out
    if not raw:
        return out
    by_name = {ExifTags.TAGS.get(k, str(k)): v for k, v in raw.items()}
    for src, dst in EXIF_KEYS.items():
        if src in by_name:
            out[dst] = _rational_to_float(by_name[src])
    return out


def luminance_histogram(luma: np.ndarray, bins: int = HIST_BINS) -> List[float]:
    hist, _ = np.histogram(np.clip(luma, 0, 1).reshape(-1), bins=bins, range=(0.0, 1.0))
    total = max(float(hist.sum()), 1.0)
    return [round(float(h) / total, 4) for h in hist]


def analyze(path: str) -> Dict[str, Any]:
    """Describe one image.  Unreadable files return an error, they do not raise.

    A culling pass walks hundreds of files; one corrupt sidecar or truncated
    frame must not abort the run and lose the results already computed.
    """
    info: Dict[str, Any] = {
        "filename": os.path.basename(path),
        "path": os.path.abspath(path),
    }
    try:
        info["bytes"] = os.path.getsize(path)
        with Image.open(path) as img:
            info["format"] = img.format
            info["mode"] = img.mode
            info["width"], info["height"] = img.size
            info["megapixels"] = round(img.size[0] * img.size[1] / 1_000_000, 2)
            info["has_icc_profile"] = img.info.get("icc_profile") is not None
            if img.info.get("icc_profile") is not None:
                try:
                    from PIL import ImageCms  # noqa: PLC0415

                    profile = ImageCms.ImageCmsProfile(img.info["icc_profile"])
                    info["icc_description"] = ImageCms.getProfileDescription(profile).strip()
                except Exception:
                    info["icc_description"] = "present (undecodable)"

        info.update(read_exif(path))

        rgb = load_rgb(path)
        luma = to_luma(rgb)
        info["luminance"] = {
            "mean": round(float(luma.mean()), 4),
            "median": round(float(np.median(luma)), 4),
            "stdev": round(float(luma.std()), 4),
            "histogram": luminance_histogram(luma),
        }
    except Exception as exc:  # unreadable files must not abort a batch
        info["error"] = "{}: {}".format(type(exc).__name__, exc)
    return info


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="analyze_image.py", description="Report deterministic image metadata."
    )
    parser.add_argument("path", help="image file or folder")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)

    reports = [analyze(p) for p in collect_images(args.path)]

    if args.json:
        print(json.dumps(
            reports[0] if len(reports) == 1 else reports,
            ensure_ascii=False, indent=2, default=str))
        return 0

    for r in reports:
        print("{}  {}x{}  {:.1f}MP  {}".format(
            r["filename"], r["width"], r["height"], r["megapixels"], r.get("format")))
        for key in ("captured_at", "camera_make", "camera_model", "lens",
                    "aperture", "shutter", "iso", "focal_length", "orientation"):
            if key in r:
                print("  {:<14} {}".format(key, r[key]))
        print("  {:<14} {}".format("icc", r.get("icc_description", "none")))
        lum = r["luminance"]
        print("  {:<14} mean={:.3f} median={:.3f} stdev={:.3f}".format(
            "luminance", lum["mean"], lum["median"], lum["stdev"]))
        print("  histogram     " + " ".join("{:.2f}".format(h) for h in lum["histogram"]))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
