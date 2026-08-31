#!/usr/bin/env python3
"""Burst duplicate detection for children's photo culling.

    duplicate_detection.py <folder> [--window 12] [--threshold 10]
                           [--json groups.json] [--keep-per-group 2]

Children's shoots are burst-heavy: ten nearly identical smiles is normal, and
delivering all ten is not.  This script clusters near-identical frames using

    perceptual similarity (pHash + dHash Hamming distance)
  + time adjacency        (EXIF capture time, else file order)

Time adjacency matters: two similar poses shot ten minutes apart are different
moments, while the same pose shot 0.3s apart is a burst.  Clustering without
the time window would over-merge an entire session.

The script only reports groups.  Which frame to keep is the agent's call -- it
combines these groups with the expression and sharpness scores from
image_quality.py.

Dependencies: pillow, numpy.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style_profile import collect_images  # noqa: E402


# --------------------------------------------------------------------------
# perceptual hashes
# --------------------------------------------------------------------------

def _dct_basis(n: int) -> np.ndarray:
    k = np.arange(n, dtype=np.float64)
    basis = np.cos(np.pi * k[:, None] * (2 * k[None, :] + 1) / (2.0 * n))
    basis[0] *= 1.0 / np.sqrt(2.0)
    return basis * np.sqrt(2.0 / n)


_DCT32 = _dct_basis(32)


def phash(path: str) -> int:
    """64-bit pHash: 32x32 DCT, top-left 8x8 AC block compared to its median."""
    with Image.open(path) as img:
        gray = np.asarray(
            img.convert("L").resize((32, 32), Image.LANCZOS), dtype=np.float64
        )
    coeffs = _DCT32 @ gray @ _DCT32.T
    block = coeffs[:8, :8].copy()
    block[0, 0] = 0.0                       # drop DC, it carries only exposure
    median = np.median(block)
    bits = (block > median).reshape(-1)
    return int("".join("1" if b else "0" for b in bits), 2)


def dhash(path: str) -> int:
    """64-bit dHash: 9x8 gradient comparison, robust to brightness changes."""
    with Image.open(path) as img:
        gray = np.asarray(
            img.convert("L").resize((9, 8), Image.LANCZOS), dtype=np.float64
        )
    bits = (gray[:, 1:] > gray[:, :-1]).reshape(-1)
    return int("".join("1" if b else "0" for b in bits), 2)


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """Combined hash distance: pHash for layout, dHash for structure."""
    return (hamming(a[0], b[0]) + hamming(a[1], b[1])) // 2


# --------------------------------------------------------------------------
# ordering
# --------------------------------------------------------------------------

def _natural_key(name: str) -> List[Any]:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def capture_orders(paths: Sequence[str]) -> List[int]:
    """Rank images by capture time when EXIF has it, else by natural filename order."""
    stamps: List[Tuple[str, float]] = []
    for p in paths:
        stamp = None
        try:
            from PIL import ExifTags  # noqa: PLC0415

            with Image.open(p) as img:
                raw = img.getexif()
            if raw:
                by_name = {ExifTags.TAGS.get(k, str(k)): v for k, v in raw.items()}
                stamp = by_name.get("DateTimeOriginal")
        except Exception:
            stamp = None
        if isinstance(stamp, str) and len(stamp) >= 19:
            try:
                import datetime as _dt

                dt = _dt.datetime.strptime(stamp[:19], "%Y:%m:%d %H:%M:%S")
                stamps.append((p, dt.timestamp()))
                continue
            except ValueError:
                pass
        stamps.append((p, float(1 << 60)))   # no EXIF: fall back to name order

    if all(s == float(1 << 60) for _, s in stamps):
        ordered = sorted(paths, key=lambda p: _natural_key(os.path.basename(p)))
    else:
        ordered = [p for p, _ in sorted(stamps, key=lambda t: t[1])]
    return [ordered.index(p) for p in paths]


# --------------------------------------------------------------------------
# clustering
# --------------------------------------------------------------------------

class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def find_duplicate_groups(
    paths: Sequence[str], window: int = 12, threshold: int = 10
) -> List[Dict[str, Any]]:
    """Cluster near-identical frames that are also adjacent in time."""
    if not paths:
        return []

    order = capture_orders(paths)
    hashes = []
    for p in paths:
        try:
            hashes.append((phash(p), dhash(p)))
        except Exception:
            hashes.append((0, 0))

    idx = sorted(range(len(paths)), key=lambda i: order[i])
    uf = _UnionFind(len(paths))

    for pos_i, i in enumerate(idx):
        for j in idx[pos_i + 1: pos_i + 1 + window]:
            if distance(hashes[i], hashes[j]) <= threshold:
                uf.union(i, j)

    buckets: Dict[int, List[int]] = {}
    for i in range(len(paths)):
        buckets.setdefault(uf.find(i), []).append(i)

    groups: List[Dict[str, Any]] = []
    for gid, members in enumerate(sorted(buckets.values(), key=lambda m: min(m))):
        members.sort(key=lambda i: order[i])
        if len(members) < 2:
            continue
        base = hashes[members[0]]
        groups.append(
            {
                "group_id": gid,
                "images": [os.path.basename(paths[i]) for i in members],
                "paths": [paths[i] for i in members],
                "max_distance": max(
                    distance(hashes[members[0]], hashes[m]) for m in members[1:]
                ),
                "hash": "{:016x}".format(base[0]),
            }
        )
    return groups


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="duplicate_detection.py", description="Cluster near-identical burst frames."
    )
    parser.add_argument("path", help="image file or folder")
    parser.add_argument("--window", type=int, default=12,
                        help="time-adjacency window (default 12 frames)")
    parser.add_argument("--threshold", type=int, default=10,
                        help="max combined hash distance (default 10)")
    parser.add_argument("--json", help="write groups as JSON to this path")
    args = parser.parse_args(argv)

    paths = collect_images(args.path)
    groups = find_duplicate_groups(
        paths, window=args.window, threshold=args.threshold
    )

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"scanned": len(paths), "groups": groups}, fh,
                      ensure_ascii=False, indent=2)
        print("wrote {}".format(args.json))

    dupes = sum(len(g["images"]) for g in groups)
    print("scanned {} image(s): {} duplicate group(s) covering {} frame(s)".format(
        len(paths), len(groups), dupes))
    for g in groups:
        print("  group {:<3} frames={:<3} max_distance={}".format(
            g["group_id"], len(g["images"]), g["max_distance"]))
        for name in g["images"]:
            print("      " + name)
    print("\nkeep 1-2 best frames per group (best expression + sharpness), "
          "reject the rest as duplicate_penalty.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
