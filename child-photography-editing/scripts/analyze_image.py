"""Read-only image metadata analysis without external image dependencies."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


def _png_info(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n") and data[12:16] == b"IHDR":
        width, height, bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
        return {"width": width, "height": height, "bitDepth": bit_depth, "colorType": color_type, "colorSpace": "RGB/RGBA" if color_type in (2, 6) else "non-RGB"}
    return {}


def analyze_image(path):
    file_path = Path(path)
    data = file_path.read_bytes()
    info = _png_info(data)
    if not info:
        info = {"width": None, "height": None, "colorSpace": "unknown"}
    info.update({"path": str(file_path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "orientation": "landscape" if (info.get("width") or 0) > (info.get("height") or 0) else "portrait-or-square"})
    return info


def main() -> int:
    parser = argparse.ArgumentParser(description="Report image metadata without modifying the source")
    parser.add_argument("path")
    args = parser.parse_args()
    print(json.dumps(analyze_image(args.path), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
