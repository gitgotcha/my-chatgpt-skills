#!/usr/bin/env python3
"""Build a contact sheet so a photographer can review a cull in one glance.

    contact_sheet.py <folder> --out contact_sheet.jpg [--cols 6] [--thumb 300]
                     [--title "session 2026-08-30"] [--scores quality.json]

AI culling is a first pass, not a final verdict.  The contact sheet is what
lets a human overrule it in seconds.  Filenames are printed under each
thumbnail so the reviewer can map a frame straight back to the CSV report.

Dependencies: pillow, numpy.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style_profile import collect_images  # noqa: E402

BACKGROUND = (24, 24, 27)
TEXT = (232, 232, 235)
MUTED = (150, 150, 158)

CJK_FONT_CANDIDATES = (
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhl.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
)


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in CJK_FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:                      # Pillow < 10.1
        return ImageFont.load_default()


def build_contact_sheet(
    paths: Sequence[str],
    out_path: str,
    cols: int = 6,
    thumb: int = 300,
    title: str | None = None,
    scores: Optional[Dict[str, Dict[str, float]]] = None,
) -> str:
    cols = max(1, cols)
    rows = (len(paths) + cols - 1) // cols
    label_h = 34 if scores else 24
    header_h = 54 if title else 12
    cell_w = thumb + 12
    cell_h = thumb + label_h + 12

    sheet = Image.new("RGB", (cols * cell_w + 12, rows * cell_h + header_h), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    title_font = load_font(22)
    label_font = load_font(14)

    if title:
        draw.text((16, 14), title, font=title_font, fill=TEXT)

    for index, path in enumerate(paths):
        r, c = divmod(index, cols)
        x0 = 6 + c * cell_w
        y0 = header_h + r * cell_h

        try:
            with Image.open(path) as img:
                img = img.convert("RGB")
                img.thumbnail((thumb, thumb), Image.LANCZOS)
        except Exception:
            img = Image.new("RGB", (thumb, thumb), (60, 60, 66))

        sheet.paste(img, (x0 + (thumb - img.width) // 2, y0 + (thumb - img.height) // 2))

        name = os.path.basename(path)
        text_y = y0 + thumb + 4
        draw.text((x0 + 2, text_y), name[:28], font=label_font, fill=TEXT)

        if scores and name in scores:
            score = scores[name]
            detail = " ".join(
                "{}={:.2f}".format(k, float(v))
                for k, v in list(score.items())[:3]
                if isinstance(v, (int, float))
            )
            if detail:
                draw.text((x0 + 2, text_y + 16), detail, font=label_font, fill=MUTED)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    sheet.save(out_path, quality=92)
    return out_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="contact_sheet.py", description="Build a culling contact sheet."
    )
    parser.add_argument("path", help="image file or folder")
    parser.add_argument("--out", default="contact_sheet.jpg")
    parser.add_argument("--cols", type=int, default=6)
    parser.add_argument("--thumb", type=int, default=300)
    parser.add_argument("--title")
    parser.add_argument("--scores", help="JSON file mapping filename -> score dict")
    args = parser.parse_args(argv)

    scores: Optional[Dict[str, Dict[str, float]]] = None
    if args.scores:
        with open(args.scores, "r", encoding="utf-8") as fh:
            scores = json.load(fh)

    paths = collect_images(args.path)
    build_contact_sheet(
        paths, args.out, cols=args.cols, thumb=args.thumb,
        title=args.title, scores=scores,
    )
    print("wrote {} ({} image(s), {} cols)".format(args.out, len(paths), args.cols))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
