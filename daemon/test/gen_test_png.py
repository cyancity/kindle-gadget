#!/usr/bin/env python3
"""生成 daemon 验收用测试图：1264x1680、8bit 灰度 16 阶 FS 抖动（与 render.py 同管线）。"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent / "out"
W, H = 1264, 1680
LEVELS = 16


def quantize(img: Image.Image) -> Image.Image:
    """转 8bit 灰度并压到 16 阶 + Floyd-Steinberg 抖动（同 render.py 口径）。"""
    g = img.convert("L")
    pal = Image.new("P", (256, 256))
    for i in range(LEVELS):
        v = round(i * 255 / (LEVELS - 1))
        for ch in range(3):
            pal.putpixel((i, ch), v)
    # palette 只取前 16 项：先把灰度图 remap 到 0..15 再放大回 0..255
    idx = g.point(lambda x: round(x * (LEVELS - 1) / 255))
    d = idx.convert("L").quantize(colors=LEVELS, dither=Image.Dither.FLOYDSTEINBERG)
    return d.convert("L").point(lambda x: round(x * 255 / (LEVELS - 1)))


def make(tag: str, subtitle: str) -> Image.Image:
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 200], fill=0)
    d.text((60, 60), f"DAEMON TEST {tag}", fill=255)
    d.text((60, 260), subtitle, fill=0)
    # 16 阶灰阶条，肉眼核对刷屏层次
    for i in range(LEVELS):
        v = round(i * 255 / (LEVELS - 1))
        x0 = i * (W // LEVELS)
        d.rectangle([x0, 400, x0 + (W // LEVELS), 700], fill=v)
    for i in range(40):
        x = (i * 97) % (W - 120)
        y = 800 + (i * 53) % 700
        d.ellipse([x, y, x + 60, y + 60], outline=0, width=3)
    return quantize(img)


def main():
    OUT.mkdir(exist_ok=True)
    for tag, sub in (("A", "cycle-1 baseline"), ("B", "cycle-2 content changed")):
        p = OUT / f"daemon-test-{tag.lower()}.png"
        make(tag, sub).save(p, optimize=True)
        print(p)


if __name__ == "__main__":
    sys.exit(main())
