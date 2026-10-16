#!/usr/bin/env python
"""把 HTML/PNG 卡片推上 Kindle 屏幕（渲染 -> 传输 -> FBInk 刷新）。

用法（契约 v2，默认走 daemon 内容池）:
    python push.py card.html                        # 渲染 1264x1680 -> 写内容池 -> GC16 全刷
    python push.py card.html --orientation landscape # 横屏 1680x1264，先切 fb 旋转再刷
    python push.py card.png                          # 跳过渲染，按方向缩放补白后写内容池
    python push.py card.html --partial               # 局部刷（GL16，无黑闪），meta force_full=0
    python push.py card.html --no-refresh            # 只写内容池，不立即刷屏（daemon 下一轮刷出）
    python push.py card.html --path /mnt/us/other.png # 直写模式（绕过内容池，老行为）

内容池：/mnt/us/qoder/daemon/current.png（tmp+mv 原子替换）+ meta（KEY=VALUE 行：
orientation=portrait|landscape、force_full=1）。立即本地 fbink 画一次；landscape 先切 fb 旋转，
portrait 先恢复 rotate=0。daemon 下一轮按 meta 方向重画同一张图，实现持久。
设备 IP 默认是示例值，环境变量 KINDLE_HOST 可覆盖。

详细说明给其他 agent 看 push.md；设备事实看 AGENTS.md。
"""

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

try:  # Windows 管道下避免 GBK 编码报错
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

REPO = Path(__file__).resolve().parent
HOST = os.environ.get("KINDLE_HOST", "192.168.1.189")  # 环境变量 KINDLE_HOST 可覆盖（示例默认值）
PORT = 2222
USER = "root"
KEY = Path.home() / ".ssh" / "kindle"
FBINK = "/mnt/us/libkh/bin/fbink"
WIDTH, HEIGHT = 1264, 1680

# 契约 v2：方向枚举与 daemon 内容池（默认推送目标，不再直写 card.png）
ORIENTATIONS = {"portrait": (WIDTH, HEIGHT), "landscape": (HEIGHT, WIDTH)}
POOL_DIR = "/mnt/us/qoder/daemon"
POOL_PNG = POOL_DIR + "/current.png"
POOL_META = POOL_DIR + "/meta"
FB_ROTATE = "/sys/class/graphics/fb0/rotate"
PORTRAIT_ROTATE = 0
# 真机验证（用户实拍确认）：landscape=3 相对产品摆放角度正确；1 上下颠倒
LANDSCAPE_ROTATE = 3

UNREACHABLE_HINT = (
    "检查 Kindle 是否休眠（按电源键）或 Wi-Fi 是否连接。\n"
    "本机侧自查：ping {host}；arp -a 看 7c-d5-66 开头的 MAC 还在不在。"
)


# Git Bash/MSYS 会把以 / 开头的参数改写成本机路径（/mnt/us/x -> C:/Program Files/Git/mnt/us/x），这里改回来
_MSYS_DEV_PATH = re.compile(
    r"(?i)^[a-z]:[\\/](?:Program Files[\\/]Git|msys64)[\\/](mnt|tmp)[\\/](.+)$"
)


def normalize_device_path(p: str) -> str:
    p = p.replace("\\", "/")
    m = _MSYS_DEV_PATH.match(p)
    if m:
        p = f"/{m.group(1)}/{m.group(2)}"
    return re.sub(r"^/+", "/", p)


def die(msg, hint=None):
    print(f"push.py: {msg}", file=sys.stderr)
    if hint:
        print(hint, file=sys.stderr)
    sys.exit(1)


def decode(data: bytes) -> str:
    if not data:
        return ""
    for enc in ("utf-8", "gbk"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", "replace")


def ssh_args(host, port):
    if not KEY.exists():
        die(f"找不到 SSH 私钥: {KEY}", "把 Kindle 的私钥放到 ~/.ssh/kindle，或改 push.py 里的 KEY。")
    exe = shutil.which("ssh")
    if exe is None:
        die("找不到 ssh 命令", "请在 Git Bash 或装有 OpenSSH 客户端的环境里运行。")
    return [
        exe,
        "-i", str(KEY),
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=8",
        "-p", str(port),
        f"{USER}@{host}",
    ]


def run_ssh(host, port, remote, stdin_file=None):
    return subprocess.run(
        ssh_args(host, port) + [remote],
        stdin=stdin_file,
        capture_output=True,
    )


def explain_failure(proc, host, port, stage):
    err = decode(proc.stderr).strip()
    low = err.lower()
    if "permission denied" in low or "authentication" in low:
        die(f"SSH 认证被拒（{host}:{port}）",
            "检查 ~/.ssh/kindle 私钥；设备重启后 dropbear 不在运行，"
            "需要在书架点 \"Qoder Run 08\" 恢复网络模式（见 AGENTS.md）。")
    if proc.returncode == 255:
        # ssh 层失败：超时/拒绝/连接被掐。设备休眠、Wi-Fi 断开、dropbear 没起、或本机代理拦截，都长这样。
        hint = UNREACHABLE_HINT.format(host=host)
        if err:
            hint += f"\nssh 输出: {err.splitlines()[-1]}"
        die(f"连不上 Kindle（{host}:{port}，{stage}失败）", hint)
    die(f"{stage}失败（ssh rc={proc.returncode}）", err or None)


def render(html: Path, args) -> Path:
    """调 render.py：Chrome 截图 -> 16 阶灰度抖动。"""
    out = REPO / "out" / f"push-{html.stem}.png"
    cmd = [
        sys.executable, str(REPO / "render.py"), str(html), "-o", str(out),
        "--width", str(args.width), "--height", str(args.height),
        "--levels", str(args.levels), "--dither", args.dither,
    ]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0 or not out.exists():
        detail = decode(proc.stderr).strip() or decode(proc.stdout).strip()
        die("渲染失败（render.py）", detail or "无输出，检查 Chrome/Edge 是否装在默认路径。")
    return out


def fit_png(png: Path, width: int, height: int) -> Path:
    """PNG 尺寸不对时等比缩放 + 白底补边，再转 16 阶灰度；尺寸正好则原样直传。"""
    from PIL import Image

    im = Image.open(png)
    if im.size == (width, height):
        return png
    src_size = im.size
    im = im.convert("RGB")
    scale = min(width / im.width, height / im.height)
    nw, nh = round(im.width * scale), round(im.height * scale)
    im = im.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGB", (width, height), "white")
    canvas.paste(im, ((width - nw) // 2, (height - nh) // 2))
    gray = canvas.convert("L").quantize(
        colors=16, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG,
    ).convert("L")
    out = REPO / "out" / f"push-{png.stem}-fit.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    gray.save(out, optimize=True)
    print(f"已按屏幕尺寸缩放补白: {png.name} {src_size} -> {out.name} {gray.size}")
    return out


def push_pool(png: Path, orientation: str, partial: bool, no_refresh: bool):
    """契约 v2 默认路径：写 daemon 内容池（tmp+mv 原子）+ meta，立即本地画一次。

    fb 旋转不在这里切：立即画之前按方向切好（横屏必须切，否则按竖屏扫描线画出花屏），
    但 meta 同步记录方向，daemon 下一轮自行校准并全刷一次，两边不会打架。
    """
    rotate = LANDSCAPE_ROTATE if orientation == "landscape" else PORTRAIT_ROTATE
    # meta 是 KEY=VALUE 行格式（daemon dashboard.sh 的 meta_get/meta_set 约定），不是 JSON
    force_full = 0 if partial else 1
    meta = f"orientation={orientation}\nforce_full={force_full}\n"
    remote = (
        f"mkdir -p {POOL_DIR} && "
        f"cat > {POOL_PNG}.tmp && mv {POOL_PNG}.tmp {POOL_PNG} && "
        f"printf '%s' '{meta}' > {POOL_META}.tmp && mv {POOL_META}.tmp {POOL_META}"
    )
    if no_refresh:
        # 只更新内容池，daemon 下一轮自己刷出
        proc = run_ssh(HOST, PORT, remote, stdin_file=open(png, "rb"))
        if proc.returncode != 0:
            explain_failure(proc, HOST, PORT, "写内容池")
        print(f"已写入内容池（按 --no-refresh 跳过立即刷屏）: {POOL_PNG}")
        print(f"meta: {meta.strip().replace(chr(10), ' ')}")
        return
    # 立即画一次：先按方向切 fb 旋转，再刷（partial 时用 GL16 局刷波形）
    waveform = "-W gl16" if partial else "-W GC16 -f"
    remote += (
        f" && echo {rotate} > {FB_ROTATE} && "
        f"{FBINK} -q {waveform} -g file={POOL_PNG}"
    )
    with open(png, "rb") as f:
        proc = run_ssh(HOST, PORT, remote, stdin_file=f)
    if proc.returncode != 0:
        explain_failure(proc, HOST, PORT, "内容池推送")
    print(f"已写入内容池: {POOL_PNG}")
    print(f"meta: {meta.strip().replace(chr(10), ' ')}")
    print(f"fb rotate={rotate}，已立即刷屏: {'GL16 局刷' if partial else 'GC16 全刷'}")
    print("daemon 下一轮将按 meta 方向校准重画。")


def transfer(png: Path, host, port, dev_path: str):
    parent = str(PurePosixPath(dev_path).parent)
    remote = f"mkdir -p {shlex.quote(parent)} && cat > {shlex.quote(dev_path)}"
    with open(png, "rb") as f:
        proc = run_ssh(host, port, remote, stdin_file=f)
    if proc.returncode != 0:
        explain_failure(proc, host, port, "传输")


def refresh(host, port, dev_path: str, partial: bool):
    if partial:
        cmd = f"{FBINK} -q -W gl16 -g file={shlex.quote(dev_path)}"
    else:
        cmd = f"{FBINK} -q -W GC16 -f -g file={shlex.quote(dev_path)}"
    proc = run_ssh(host, port, cmd)
    if proc.returncode != 0:
        explain_failure(proc, host, port, "刷屏")


def main():
    ap = argparse.ArgumentParser(
        description="把 HTML/PNG 卡片推上 Kindle 屏幕（默认写 daemon 内容池，详见 push.md）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("card", type=Path, help="HTML 或 PNG 卡片路径")
    ap.add_argument("--orientation", choices=sorted(ORIENTATIONS), default="portrait",
                    help="屏幕方向：portrait=1264x1680（默认）/ landscape=1680x1264")
    ap.add_argument("--partial", action="store_true",
                    help="局部刷（GL16 波形，无黑闪），适合内容小改；meta force_full=0")
    ap.add_argument("--path", default=None,
                    help="直写模式的设备侧目标路径（默认不走直写，统一写 daemon 内容池）")
    ap.add_argument("--no-refresh", action="store_true", help="只写文件，不立即刷屏")
    ap.add_argument("--host", default=HOST, help=argparse.SUPPRESS)
    ap.add_argument("--levels", type=int, default=16, help="灰阶数（默认 16）")
    ap.add_argument("--dither", choices=["floyd", "none"], default="floyd", help="抖动方式")
    args = ap.parse_args()
    # 渲染/补白尺寸完全由方向决定（契约 v2）
    args.width, args.height = ORIENTATIONS[args.orientation]

    card = args.card
    if not card.exists():
        die(f"找不到输入文件: {card}")
    card = card.resolve()
    ext = card.suffix.lower()

    if ext in (".html", ".htm"):
        png = render(card, args)
        print(f"已渲染: {png.name}（{args.orientation} {args.width}x{args.height}）")
    elif ext == ".png":
        png = fit_png(card, args.width, args.height)
    else:
        die(f"只支持 .html/.htm/.png 输入，收到的是: {ext or '(无扩展名)'}")

    # 默认（契约 v2）：写 daemon 内容池 + meta，立即本地画一次，daemon 下一轮按方向重画
    if args.path is None:
        push_pool(png, args.orientation, args.partial, args.no_refresh)
        return

    # 直写模式（绕过内容池，老行为）：手动指定 --path 才生效
    dev_path = normalize_device_path(args.path)
    if not dev_path.startswith("/"):
        die(f"--path 必须是设备上的绝对路径，收到: {args.path}")
    if "/qoder/daemon/" in dev_path:
        die("--path 不能指向 /mnt/us/qoder/daemon/（内容池只能通过默认推送流程写入）")

    transfer(png, args.host, PORT, dev_path)
    print(f"已传输: {png.name} -> {args.host}:{dev_path}")

    if args.no_refresh:
        print("按 --no-refresh 跳过刷屏")
        return
    refresh(args.host, PORT, dev_path, args.partial)
    print(f"已刷屏: {'GL16 局刷' if args.partial else 'GC16 全刷'}")


if __name__ == "__main__":
    main()
