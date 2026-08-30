"""Deterministic synthetic fixtures for the child-photoShop-skill tests.

The tests must not depend on real photographs of real children: that would
mean shipping minors' images in a public repository.  Synthetic images are
also better test data -- they are reproducible, and their properties
(warmth, brightness, sharpness, near-duplication) are known by construction.

Every builder returns the path it wrote.
"""

from __future__ import annotations

import os
from typing import Tuple

import numpy as np
from PIL import Image, ImageFilter

SEED = 3


def _grid(height: int, width: int) -> Tuple[np.ndarray, np.ndarray]:
    yy = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    xx = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :]
    return yy * np.ones((height, width), dtype=np.float32), np.ones(
        (height, width), dtype=np.float32
    ) * xx


def _subject_mask(height: int, width: int) -> np.ndarray:
    """An oval roughly where a child's face would sit."""
    yy, xx = _grid(height, width)
    return (((xx - 0.5) / 0.13) ** 2 + ((yy - 0.58) / 0.20) ** 2) < 1.0


def _save(array: np.ndarray, path: str, quality: int = 95) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    Image.fromarray((np.clip(array, 0.0, 1.0) * 255).astype(np.uint8)).save(
        path, quality=quality
    )
    return path


def build_warm_reference(path: str, height: int = 600, width: int = 800) -> str:
    """A warm, soft, bright camping-style frame: beige + olive + skin tones."""
    rng = np.random.default_rng(SEED)
    yy, xx = _grid(height, width)

    img = np.zeros((height, width, 3), dtype=np.float32)
    img[..., 0] = 0.80 - 0.10 * yy
    img[..., 1] = 0.63 - 0.10 * yy
    img[..., 2] = 0.42 - 0.08 * yy

    # olive accent, lower left
    img[int(height * 0.6):, : int(width * 0.35)] = [0.35, 0.40, 0.24]

    # soft key light, upper centre
    glow = np.exp(-(((xx - 0.5) ** 2) / 0.10 + ((yy - 0.28) ** 2) / 0.10))
    img += glow[..., None] * 0.16

    img[_subject_mask(height, width)] = [0.91, 0.77, 0.63]
    img += rng.normal(0.0, 0.006, img.shape).astype(np.float32)
    return _save(img, path)


def build_cool_target(path: str, height: int = 600, width: int = 800) -> str:
    """A cool, dim, flat frame -- deliberately the opposite of the reference."""
    rng = np.random.default_rng(SEED + 1)
    img = np.zeros((height, width, 3), dtype=np.float32)
    img[..., 0] = 0.34
    img[..., 1] = 0.40
    img[..., 2] = 0.50
    img[_subject_mask(height, width)] = [0.72, 0.62, 0.58]
    img += rng.normal(0.0, 0.004, img.shape).astype(np.float32)
    return _save(img, path)


def _texture(height: int, width: int, amplitude: float = 0.03) -> np.ndarray:
    """Deterministic fine detail, identical across frames.

    Random per-image noise cannot be used here.  With it, dHash's
    neighbour-pixel comparisons across flat regions are decided by noise, so
    two visually identical frames hash far apart and duplicate detection
    learns nothing.  Laplacian variance has the same problem from the other
    side: random noise inflates it, so a noisy frame looks "sharper" than a
    clean one.  A fixed texture keeps both metrics honest.
    """
    yy = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    xx = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :]
    fine = np.sin(120.0 * xx) * np.sin(95.0 * yy)
    coarse = np.sin(31.0 * xx + 0.7) * np.sin(27.0 * yy + 1.3)
    return (amplitude * (0.6 * fine + 0.4 * coarse)).astype(np.float32)


def _studio_frame(height: int, width: int, subject_box=(100, 200, 150, 250)) -> np.ndarray:
    frame = np.zeros((height, width, 3), dtype=np.float32)
    frame[..., 0] = 0.55
    frame[..., 1] = 0.50
    frame[..., 2] = 0.45
    y0, y1, x0, x1 = subject_box
    frame[y0:y1, x0:x1] = [0.85, 0.70, 0.60]
    return frame + _texture(height, width)[..., None]


def build_burst(directory: str, count: int = 5, height: int = 300, width: int = 400) -> list:
    """`count` near-identical burst frames plus one clearly different frame.

    The burst frames differ only by a tiny, realistic variation (a fraction of
    a pixel of exposure), the way a real burst does.  The last frame changes
    composition, so it must NOT be grouped with them.
    """
    os.makedirs(directory, exist_ok=True)
    paths = []
    for i in range(count):
        frame = _studio_frame(height, width) * (1.0 + 0.004 * i)
        paths.append(_save(frame, os.path.join(directory, "IMG_{:04d}.jpg".format(i + 1))))

    # genuinely different: subject moved and the background changed
    other = _studio_frame(height, width, subject_box=(60, 240, 40, 150))
    other[..., 2] += 0.18
    paths.append(_save(other, os.path.join(directory, "IMG_{:04d}.jpg".format(count + 1))))
    return paths


def build_blurry(path: str, height: int = 300, width: int = 400) -> str:
    """Same frame as the burst, defocused -- must score lower on sharpness."""
    frame = np.clip(_studio_frame(height, width), 0.0, 1.0)
    img = Image.fromarray((frame * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5))
    return _save(np.asarray(img, dtype=np.float32) / 255.0, path)


def build_all(directory: str) -> dict:
    """Populate `directory` with the full fixture set and return the paths."""
    os.makedirs(directory, exist_ok=True)
    burst_dir = os.path.join(directory, "burst")
    return {
        "reference": build_warm_reference(os.path.join(directory, "ref_camping.jpg")),
        "target": build_cool_target(os.path.join(directory, "target_cool.jpg")),
        "blur": build_blurry(os.path.join(directory, "blurry.jpg")),
        "burst": build_burst(burst_dir),
        "burst_dir": burst_dir,
        "dir": directory,
    }
