#!/usr/bin/env python3
"""Build the ephemera.photography site: reads content/, writes the static site to docs/.

Usage: python3 build.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent
GRID_PX = 800        # long edge of images in the photo grids and small tiles
FULL_PX = 2000       # long edge of images in the full-screen viewer and the wide home tile
PORTRAIT_PX = 1200   # long edge of the about-page portrait
JPEG_QUALITY = 82


def process_image(src: Path, dest: Path, max_px: int) -> tuple[int, int]:
    """Save src as a JPEG at most max_px on its long edge, without camera metadata.

    Skips the work when dest is already newer than src. Returns dest's (width, height).
    """
    if dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
        with Image.open(dest) as done:
            return done.size
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as original:
        icc = original.info.get("icc_profile")
        im = ImageOps.exif_transpose(original)
        if im.mode != "RGB":
            im = im.convert("RGB")
        im.thumbnail((max_px, max_px), Image.LANCZOS)
        im.save(dest, "JPEG", quality=JPEG_QUALITY, progressive=True, optimize=True, icc_profile=icc)
        return im.size
