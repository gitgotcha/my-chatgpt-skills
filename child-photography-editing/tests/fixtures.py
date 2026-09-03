"""Synthetic metadata fixtures; these are not photographs."""
from __future__ import annotations

import struct


def synthetic_png(width: int, height: int) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", len(ihdr)) + b"IHDR" + ihdr


def synthetic_jpeg(width: int, height: int) -> bytes:
    app0 = b"\xff\xe0\x00\x04JF"
    sof0_payload = struct.pack(">BHHB", 8, height, width, 3) + b"\x01\x11\x00\x02\x11\x00\x03\x11\x00"
    sof0 = b"\xff\xc0" + struct.pack(">H", len(sof0_payload) + 2) + sof0_payload
    return b"\xff\xd8" + app0 + sof0 + b"\xff\xd9"
