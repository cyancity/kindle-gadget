"""kindle-studio 托盘主程序：右下角常驻，工作台 http://127.0.0.1:8762。

托盘菜单：
  - 打开工作台（双击托盘图标同效）
  - Kindle：恢复正常模式 / 看板模式（SSH 到设备切换 UI 框架与 daemon）
  - 退出

HTTP server 与本进程同生命周期（import studio/server.py 的 Handler）。
"""
import importlib.util
import os
import threading
import webbrowser
import subprocess
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parent.parent
STUDIO_DIR = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8762"
SSH = ["ssh", "-i", str(Path.home() / ".ssh" / "kindle"),
       "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
       "-p", "2222", "root@" + os.environ.get("KINDLE_HOST", "192.168.1.189")]

_spec = importlib.util.spec_from_file_location("studio_server", STUDIO_DIR / "server.py")
srv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(srv)  # 执行 server.py 顶层（定义 Handler 与常量）

_http = None
_icon = None


def start_http():
    global _http
    if _http:
        return
    _http = srv.ThreadingHTTPServer(("127.0.0.1", srv.PORT), srv.Handler)
    threading.Thread(target=_http.serve_forever, daemon=True).start()


def ssh_run(remote: str) -> str:
    r = subprocess.run(SSH, input=remote.encode(), capture_output=True, timeout=60)
    return (r.stdout + r.stderr).decode("utf-8", "replace").strip()


def kindle_normal(icon, item):
    """恢复正常模式：停 daemon、起 UI 框架、竖屏、释放防休眠。"""
    def work():
        out = ssh_run(
            "kill $(cat /mnt/us/qoder/daemon/daemon.pid 2>/dev/null) 2>/dev/null; "
            "pkill -f '[d]ashboard.sh' 2>/dev/null; "
            "lipc-set-prop -i com.lab126.powerd preventScreenSaver 0; "
            "initctl start framework; initctl start lab126_gui; "
            "echo 0 > /sys/class/graphics/fb0/rotate; echo NORMAL_OK")
        print("normal mode:", out[-200:], flush=True)
    threading.Thread(target=work, daemon=True).start()


def kindle_dashboard(icon, item):
    """看板模式：停 UI 框架、防休眠、起 daemon。"""
    def work():
        out = ssh_run(
            "initctl stop lab126_gui 2>/dev/null; initctl stop framework 2>/dev/null; "
            "lipc-set-prop -i com.lab126.powerd preventScreenSaver 1; "
            "setsid sh /mnt/us/qoder/daemon/start.sh >/dev/null 2>&1 & sleep 3; "
            "tail -2 /mnt/us/qoder/daemon/daemon.log; echo DASH_OK")
        print("dashboard mode:", out[-300:], flush=True)
    threading.Thread(target=work, daemon=True).start()


def open_workbench(icon=None, item=None):
    start_http()
    webbrowser.open(URL)


def make_icon() -> Image.Image:
    """纸感小图标：米白圆角底 + 铜棕墨线 e-ink 屏。"""
    im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 4, 60, 60), radius=12, fill=(250, 248, 244, 255))
    d.rounded_rectangle((14, 10, 50, 48), radius=3, outline=(138, 90, 46, 255), width=3)
    d.rectangle((20, 17, 44, 20), fill=(138, 90, 46, 255))
    d.rectangle((20, 25, 40, 28), fill=(43, 40, 34, 160))
    d.rectangle((20, 33, 42, 36), fill=(43, 40, 34, 160))
    d.rounded_rectangle((22, 52, 42, 56), radius=2, fill=(138, 90, 46, 255))
    return im


def quit_app(icon, item):
    icon.stop()


def main():
    global _icon
    start_http()
    menu = pystray.Menu(
        pystray.MenuItem("打开工作台", lambda i, it: open_workbench(), default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Kindle：恢复正常模式", kindle_normal),
        pystray.MenuItem("Kindle：看板模式", kindle_dashboard),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", quit_app),
    )
    _icon = pystray.Icon("kindle-studio", make_icon(), "kindle-studio", menu)
    print(f"kindle-studio tray running, workbench at {URL}", flush=True)
    try:
        _icon.run()
    finally:
        if _http:
            _http.shutdown()


if __name__ == "__main__":
    main()
