#!/usr/bin/env python3
"""
Argos 플레이스홀더 애셋 생성 스크립트.

Pillow 없이 순수 Python + struct 로 최소 PNG 생성.
cv2(numpy) 가 있으면 cv2로 더 깔끔하게 렌더링.
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"


def _ensure_dir():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def _generate_with_cv2():
    """OpenCV + numpy 로 아이콘/스플래시 생성."""
    import cv2
    import numpy as np

    # ── icon.png (256×256) ─────────────────────────────────────────────
    icon = np.full((256, 256, 3), (46, 26, 26), dtype=np.uint8)  # #1A1A2E BGR
    # 중앙 원
    cv2.circle(icon, (128, 128), 80, (229, 136, 30), -1)  # #1E88E5 BGR
    # "A" 텍스트
    cv2.putText(
        icon, "A", (88, 168),
        cv2.FONT_HERSHEY_SIMPLEX, 3.0, (224, 224, 224), 6,
        cv2.LINE_AA,
    )
    cv2.imwrite(str(ASSETS_DIR / "icon.png"), icon)
    print(f"  Created: {ASSETS_DIR / 'icon.png'}")

    # ── splash.png (600×400) ──────────────────────────────────────────
    splash = np.full((400, 600, 3), (46, 26, 26), dtype=np.uint8)
    # 상단 악센트 바
    splash[0:4, :] = (229, 136, 30)
    # 중앙 텍스트
    cv2.putText(
        splash, "Argos", (140, 220),
        cv2.FONT_HERSHEY_SIMPLEX, 2.5, (229, 136, 30), 4,
        cv2.LINE_AA,
    )
    cv2.putText(
        splash, "AI Vision Engineer Agent", (120, 280),
        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (158, 158, 158), 2,
        cv2.LINE_AA,
    )
    cv2.putText(
        splash, "v1.0.0", (260, 340),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (97, 97, 97), 1,
        cv2.LINE_AA,
    )
    cv2.imwrite(str(ASSETS_DIR / "splash.png"), splash)
    print(f"  Created: {ASSETS_DIR / 'splash.png'}")


def _generate_minimal_png(path: Path, width: int, height: int, r: int, g: int, b: int):
    """zlib + struct 로 최소 단색 PNG 생성 (Pillow/cv2 없는 환경 폴백)."""
    import struct
    import zlib

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    # IHDR
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    # IDAT — uncompressed scanlines (filter byte 0 + RGB per pixel)
    raw_row = b"\x00" + bytes([r, g, b]) * width
    raw_image = raw_row * height
    idat_data = zlib.compress(raw_image)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr_data)
    png += chunk(b"IDAT", idat_data)
    png += chunk(b"IEND", b"")

    path.write_bytes(png)
    print(f"  Created (minimal): {path}")


def main():
    print("Generating Argos placeholder assets...")
    _ensure_dir()

    try:
        _generate_with_cv2()
    except ImportError:
        print("  cv2 not available — falling back to minimal PNG generation")
        _generate_minimal_png(ASSETS_DIR / "icon.png", 256, 256, 0x1A, 0x1A, 0x2E)
        _generate_minimal_png(ASSETS_DIR / "splash.png", 600, 400, 0x1A, 0x1A, 0x2E)

    print("Done.")


if __name__ == "__main__":
    main()
