"""Grab the Kindle framebuffer and save it as a PNG.

fb geometry (probed on device): virtual 1696x2560 @8bpp -> row stride 1696 bytes.
portrait (rotate=0): visible 1264x1680 at the top-left of the dump.
landscape (rotate=3): the panel shows a 1680x1264 view that lives in the dump as a
1680x1264 band at the top (stride still 1696), already upright - just crop, no
rotation (verified 2026-10-17 on a live daemon-drawn card; the earlier
"crop + ROTATE_90" recipe was wrong).

Usage: python screenshot.py [-o out/kindle-screen.png] [--landscape]
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image

KEY = str(Path.home() / ".ssh" / "kindle")
TARGET = "root@" + os.environ.get("KINDLE_HOST", "192.168.1.189")
VISIBLE_W, VISIBLE_H, STRIDE = 1264, 1680, 1696


def grab(out: Path, landscape: bool) -> Path:
    ssh = [
        "ssh", "-i", KEY,
        "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
        "-p", "2222", TARGET,
        "cat /dev/fb0",
    ]
    r = subprocess.run(ssh, capture_output=True)
    if r.returncode != 0:
        sys.exit(f"ssh failed rc={r.returncode}: {r.stderr.decode('utf-8', 'replace')[-500:]}")
    raw = r.stdout
    need = STRIDE * VISIBLE_H
    if len(raw) < need:
        sys.exit(f"fb dump too small: {len(raw)} bytes < {need}")
    im = Image.frombytes("L", (STRIDE, VISIBLE_H), bytes(raw[:need]))
    if landscape:
        # rotate=3: upright 1680x1264 band at the top of the dump (stride 1696)
        im = im.crop((0, 0, VISIBLE_H, VISIBLE_W))
    else:
        im = im.crop((0, 0, VISIBLE_W, VISIBLE_H))
    im.save(out, optimize=True)
    print(f"{out}  {im.size[0]}x{im.size[1]}  bytes={out.stat().st_size}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", type=Path, default=Path("out/kindle-screen.png"))
    ap.add_argument("--landscape", action="store_true")
    a = ap.parse_args()
    grab(a.out, a.landscape)
