#!/usr/bin/env python3
"""kindle-gadget 看板 daemon 控制脚本（PC 侧）。

用法:
  python daemon/kd.py start                  # 部署脚本+启动（幂等）
  python daemon/kd.py stop | restart | status
  python daemon/kd.py log [-n 20]            # 看设备日志尾部
  python daemon/kd.py push <png> [--full]    # 原子推送看板图，下一轮刷出
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

HOST = os.environ.get("KINDLE_HOST", "192.168.1.189")
PORT = 2222
USER = "root"
KEY = os.path.expanduser("~/.ssh/kindle")
REMOTE = "/mnt/us/qoder/daemon"
DEVICE_DIR = Path(__file__).resolve().parent / "device"


def die(msg: str, code: int = 1):
    print(f"[kd] {msg}")
    sys.exit(code)


def ssh(cmd, stdin_bytes=None, timeout: int = 30, check: bool = True):
    r = subprocess.run(
        ["ssh", "-i", KEY,
         "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
         "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=8",
         "-p", str(PORT), f"{USER}@{HOST}", cmd],
        input=stdin_bytes, capture_output=True, timeout=timeout)
    if check and r.returncode != 0:
        die(f"remote command failed rc={r.returncode}: {cmd}\n{r.stderr.decode(errors='replace')}", 2)
    return r


def alive() -> bool:
    try:
        return ssh("echo ok", timeout=10).stdout.strip() == b"ok"
    except (subprocess.TimeoutExpired, OSError):
        return False


def push_bytes(remote_path: str, data: bytes):
    ssh(f"cat > {remote_path}", stdin_bytes=data, timeout=60)


def push_file(local: Path, remote_path: str):
    print(f"[kd] push {local.name} -> {remote_path}")
    push_bytes(remote_path, local.read_bytes())
    ssh(f"chmod 755 {remote_path}")


def deploy(force_config: bool = False):
    if not alive():
        die(f"设备失联（ssh {HOST}:{PORT} 不通）。先 ping + arp 查 7c-d5-66，还不通就是 Wi-Fi/休眠问题", 3)
    ssh(f"mkdir -p {REMOTE}")
    for name in ("dashboard.sh", "start.sh", "stop.sh"):
        push_file(DEVICE_DIR / name, f"{REMOTE}/{name}")
    if force_config or ssh(f"[ -f {REMOTE}/config ]", check=False).returncode != 0:
        print("[kd] push config (device config absent)")
        push_bytes(f"{REMOTE}/config", (DEVICE_DIR / "config").read_bytes())


def cmd_start(_a):
    deploy()
    try:
        r = ssh(f"sh {REMOTE}/start.sh")
        print(r.stdout.decode().strip())
    except subprocess.TimeoutExpired:
        print("[kd] start 命令超时：battery 模式下设备可能在启动后立即挂起（属预期），"
              "等唤醒窗口或临时切 MODE=ac")
    print()
    try:
        cmd_status(None, quiet_first=True)
    except (subprocess.TimeoutExpired, OSError):
        print("[kd] status 超时：设备可能已挂起（battery 模式属预期）")


def cmd_stop(_a):
    if not alive():
        die("设备失联，无法 stop", 3)
    r = ssh(f"sh {REMOTE}/stop.sh")
    print(r.stdout.decode().strip())


def cmd_status(_a, quiet_first: bool = False):
    snippet = f"""
cd {REMOTE} || exit 1
pid=$(cat daemon.pid 2>/dev/null)
if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
  echo "daemon: RUNNING pid=$pid"
else
  echo "daemon: NOT running"
fi
echo "config: $(grep -v '^#' config 2>/dev/null | tr '\\n' ' ')"
echo "battery: $(gasgauge-info -c 2>/dev/null) charging=$(lipc-get-prop -i com.lab126.powerd isCharging 2>/dev/null)"
ls -l current.png 2>/dev/null | awk '{{print "current.png:", $5, "bytes", $6, $7, $8}}'
[ -f meta ] && echo "meta: $(tr '\\n' ' ' < meta)"
echo "--- log tail ---"
tail -n 6 daemon.log 2>/dev/null
"""
    r = ssh(snippet)
    if not quiet_first:
        print()
    print(r.stdout.decode(errors="replace").strip())


def cmd_log(a):
    r = ssh(f"tail -n {a.n} {REMOTE}/daemon.log")
    print(r.stdout.decode(errors="replace").strip())


def cmd_push(a):
    png = Path(a.png)
    if not png.exists():
        die(f"文件不存在: {png}")
    data = png.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        die("不是 PNG（魔数不符）")
    try:
        if not a.force:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(data))
            if img.size != (1264, 1680):
                die(f"尺寸 {img.size} != (1264, 1680)，先过 render.py（或 --force 强推）")
    except ImportError:
        print("[kd] 本机无 Pillow，跳过尺寸检查")

    if not alive():
        die("设备失联", 3)
    ssh(f"mkdir -p {REMOTE}")
    push_bytes(f"{REMOTE}/current.png.tmp", data)
    ssh(f"mv {REMOTE}/current.png.tmp {REMOTE}/current.png && sync")
    if a.full:
        ssh(f"sh -c 'touch {REMOTE}/meta; "
            f"if grep -q \"^[[:space:]]*force_full=\" {REMOTE}/meta; then "
            f"sed -i \"s/^[[:space:]]*force_full[[:space:]]*=.*/force_full=1/\" {REMOTE}/meta; "
            f"else echo force_full=1 >> {REMOTE}/meta; fi'")
        print("[kd] meta force_full=1 已置")
    interval = ssh(f"grep '^INTERVAL=' {REMOTE}/config 2>/dev/null | cut -d= -f2").stdout.decode().strip() or "60"
    print(f"[kd] pushed {png.name}，daemon 下一轮（<= {interval}s）刷出")


def main():
    p = argparse.ArgumentParser(description="kindle 看板 daemon 控制")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("start")
    sub.add_parser("stop")
    sub.add_parser("restart")
    sub.add_parser("status")
    lp = sub.add_parser("log")
    lp.add_argument("-n", type=int, default=20)
    pp = sub.add_parser("push")
    pp.add_argument("png")
    pp.add_argument("--full", action="store_true", help="下一轮强制全刷")
    pp.add_argument("--force", action="store_true", help="跳过尺寸检查")
    a = p.parse_args()

    if a.cmd == "start":
        cmd_start(a)
    elif a.cmd == "stop":
        cmd_stop(a)
    elif a.cmd == "restart":
        cmd_stop(a)
        cmd_start(a)
    elif a.cmd == "status":
        cmd_status(a)
    elif a.cmd == "log":
        cmd_log(a)
    elif a.cmd == "push":
        cmd_push(a)


if __name__ == "__main__":
    main()
