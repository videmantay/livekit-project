# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=11", "numpy>=2"]
# ///
"""Turn a green-screen photo of Lee into a transparent WebP for the landing page.

Usage: uv run scripts/cutout.py <input.png> <output.webp> [--width 1200] [--blank-tab]

--blank-tab clears the dark-green tab in the top-left corner that some exports carry.
"""

import argparse

import numpy as np
from PIL import Image, ImageFilter


def cutout(src: str, dst: str, width: int, blank_tab: bool) -> None:
    im = Image.open(src).convert("RGB")
    rgb = np.asarray(im).astype(np.float32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]

    # How much greener a pixel is than its other channels. Skin, hair and the grey shirt
    # sit near zero or below; the backdrop sits well above.
    spill = g - np.maximum(r, b)
    # Measured on the current shoot: backdrop 45-57, shirt and hair under 6.
    lo, hi = 10.0, 30.0
    alpha = 1.0 - np.clip((spill - lo) / (hi - lo), 0.0, 1.0)

    if blank_tab:
        h, w = alpha.shape
        alpha[: int(h * 0.11), : int(w * 0.24)] = 0.0

    # Soften the matte edge and drop stray specks in the backdrop.
    a_img = Image.fromarray((alpha * 255).astype(np.uint8))
    a_img = a_img.filter(ImageFilter.MedianFilter(5)).filter(ImageFilter.GaussianBlur(1.2))
    alpha = np.asarray(a_img).astype(np.float32) / 255.0

    # Despill: cap green at the larger of red and blue so edges lose the green fringe.
    g = np.minimum(g, np.maximum(r, b) + 4)
    out = np.dstack([r, g, b, alpha * 255]).clip(0, 255).astype(np.uint8)

    img = Image.fromarray(out, "RGBA")
    bbox = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if bbox:
        img = img.crop(bbox)
    if img.width > width:
        img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    img.save(dst, "WEBP", quality=82, method=6)
    print(f"{dst}: {img.width}x{img.height}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--width", type=int, default=1200)
    p.add_argument("--blank-tab", action="store_true")
    a = p.parse_args()
    cutout(a.src, a.dst, a.width, a.blank_tab)
