"""Read-only image metadata analysis without external image dependencies."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


def _png_info(data):
    if len(data) >= 26 and data.startswith(b"\x89PNG\r\n\x1a\n") and data[12:16] == b"IHDR":
        width, height, bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
        return {"width": width, "height": height, "bitDepth": bit_depth, "colorType": color_type, "colorSpace": "RGB/RGBA" if color_type in (2, 6) else "non-RGB"}
    return {}


JPEG_SOF_MARKERS = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def _jpeg_info(data):
    if not data.startswith(b"\xff\xd8"):
        return {}
    offset = 2
    while offset < len(data):
        if data[offset] != 0xFF:
            return {}
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            return {}
        marker = data[offset]
        offset += 1
        if marker in {0xD8, 0x01} or 0xD0 <= marker <= 0xD7:
            continue
        if marker in {0xD9, 0xDA} or offset + 2 > len(data):
            return {}
        segment_length = struct.unpack(">H", data[offset : offset + 2])[0]
        if segment_length < 2 or offset + segment_length > len(data):
            return {}
        if marker in JPEG_SOF_MARKERS:
            if segment_length < 8:
                return {}
            bit_depth = data[offset + 2]
            height, width = struct.unpack(">HH", data[offset + 3 : offset + 7])
            components = data[offset + 7]
            color_space = {1: "grayscale", 3: "YCbCr", 4: "CMYK"}.get(components, "unknown")
            return {"width": width, "height": height, "bitDepth": bit_depth, "colorSpace": color_space}
        offset += segment_length
    return {}


def analyze_image(path):
    file_path = Path(path)
    with file_path.open("rb") as image_file:
        data = image_file.read()
    info = _png_info(data) or _jpeg_info(data)
    if not info:
        info = {"width": None, "height": None, "colorSpace": "unknown"}
    width = info.get("width")
    height = info.get("height")
    if width is None or height is None:
        orientation = "unknown"
    else:
        orientation = "landscape" if width > height else "portrait-or-square"
    info.update({"path": str(file_path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "orientation": orientation})
    return info


def main() -> int:
    parser = argparse.ArgumentParser(description="Report image metadata without modifying the source")
    parser.add_argument("path")
    args = parser.parse_args()
    try:
        result = analyze_image(args.path)
    except OSError as exc:
        parser.error(f"cannot read image {args.path}: {exc}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
