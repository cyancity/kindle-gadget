import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image

CHROME = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
]


def shoot(html: Path, raw: Path, width: int, height: int) -> None:
    browser = next((p for p in CHROME if p.exists()), None)
    if browser is None:
        sys.exit("no chromium browser found")
    raw.parent.mkdir(parents=True, exist_ok=True)
    url = html.resolve().as_uri()
    cmd = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--screenshot={raw.resolve()}",
        f"--window-size={width},{height}",
        url,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if not raw.exists():
        sys.exit(f"browser produced no screenshot (rc={r.returncode}):\n{r.stderr[-1500:]}")


def to_gray(raw: Path, out: Path, levels: int, dither: str) -> None:
    im = Image.open(raw).convert("L")
    if levels < 256:
        im = im.quantize(
            colors=levels,
            method=Image.Quantize.MEDIANCUT,
            dither={"floyd": Image.Dither.FLOYDSTEINBERG, "none": Image.Dither.NONE}[dither],
        ).convert("L")
    im.save(out, optimize=True)
    print(f"{out}  {im.size[0]}x{im.size[1]}  mode={im.mode}  bytes={out.stat().st_size}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("html", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--width", type=int, default=1264)
    ap.add_argument("--height", type=int, default=1680)
    ap.add_argument("--levels", type=int, default=16)
    ap.add_argument("--dither", choices=["floyd", "none"], default="floyd")
    a = ap.parse_args()
    raw = a.out.with_suffix(".raw.png")
    shoot(a.html, raw, a.width, a.height)
    im = Image.open(raw)
    if im.size != (a.width, a.height):
        im = im.resize((a.width, a.height), Image.LANCZOS)
    im.save(raw)
    to_gray(raw, a.out, a.levels, a.dither)
    raw.unlink()
