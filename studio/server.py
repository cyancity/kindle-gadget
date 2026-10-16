"""kindle-studio local server: edit HTML cards, preview the real e-ink PNG, push to Kindle.

Bind 127.0.0.1:8762 only. Stdlib only.
契约 v2：/api/render、/api/push、/api/ai-edit 支持 orientation（portrait/landscape）；
推送统一写 daemon 内容池（current.png + meta），不再直写 card.png。
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent.parent
STUDIO = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import render  # noqa: E402  (repo-root render.py: HTML -> browser shot -> gray dither)
import card_store  # noqa: E402  (studio/card_store.py: 卡片版本化存储，同目录)

CARDS = ROOT / "cards"
OUT = ROOT / "out"
TASKS = STUDIO / "agent_tasks"
PORT = 8762

MAGPIE = "http://127.0.0.1:3425/v1/chat/completions"
AI_MODEL = os.environ.get("STUDIO_AI_MODEL", "group/auto-claude-sonnet-5-5")
AI_TIMEOUT = 300

def ai_system_prompt(width: int, height: int) -> str:
    return f"""你是墨水屏卡片排版助手。用户给你一张 {width}×{height} 的 Kindle 卡片 HTML，
以及若干圈注区域（坐标基于该尺寸）和修改要求。你输出修改后的完整 HTML。
硬约束：
- body 固定 width:{width}px; height:{height}px，白底黑字，系统字体
- 禁止 flex gap、position:fixed/sticky、CSS 动画/过渡、emoji
- 任何文字字号不小于 30px
- 只改与要求相关的部分，其余保持原样
- 只输出 HTML 代码本身，不要解释，不要 markdown 代码围栏"""

SSH_KEY = Path.home() / ".ssh" / "kindle"
SSH_TARGET = "root@" + os.environ.get("KINDLE_HOST", "192.168.1.189")

# 契约 v2：方向枚举（portrait 为默认）
ORIENTATIONS = {"portrait": (1264, 1680), "landscape": (1680, 1264)}
DEFAULT_ORIENTATION = "landscape"

# daemon 内容池（契约 v2）：/api/push 不再直写 card.png，统一写内容池，
# daemon 下一轮按 meta 里的方向重画同一张图，实现持久
DEVICE_DAEMON_DIR = "/mnt/us/qoder/daemon"
POOL_PNG = DEVICE_DAEMON_DIR + "/current.png"
POOL_META = DEVICE_DAEMON_DIR + "/meta"
FBINK = "/mnt/us/libkh/bin/fbink"
FB_ROTATE = "/sys/class/graphics/fb0/rotate"
PORTRAIT_ROTATE = 0
# 真机验证（用户实拍确认）：landscape=3 相对产品摆放角度正确；1 上下颠倒
LANDSCAPE_ROTATE = 3


def render_html_to_png(html_text: str, out_png: Path,
                       orientation: str = DEFAULT_ORIENTATION) -> Path:
    width, height = ORIENTATIONS[orientation]
    html_file = OUT / "_studio_card.html"
    html_file.parent.mkdir(parents=True, exist_ok=True)
    html_file.write_text(html_text, encoding="utf-8", newline="\n")
    raw = out_png.with_suffix(".raw.png")
    render.shoot(html_file, raw, width, height)
    with render.Image.open(raw) as im:  # close the lazy handle before unlink (Windows locks)
        if im.size != (width, height):
            im = im.resize((width, height), render.Image.LANCZOS)
            im.save(raw)
    render.to_gray(raw, out_png, 16, "floyd")
    raw.unlink(missing_ok=True)
    return out_png


def push_png_to_device(png: Path, orientation: str) -> tuple[bool, str]:
    """契约 v2 推送：写 daemon 内容池（tmp+mv 原子）-> 按 meta 方向 -> 立即本地 fbink 全刷一次。

    meta 是 KEY=VALUE 行格式（设备 daemon 的 meta_get 约定），不是 JSON。
    """
    rotate = LANDSCAPE_ROTATE if orientation == "landscape" else PORTRAIT_ROTATE
    meta = f"orientation={orientation}\nforce_full=1\n"
    # 一条 ssh 串完四步：原子写 PNG -> 原子写 meta -> 按方向切 fb 旋转 -> GC16 全刷
    remote = (
        f"mkdir -p {DEVICE_DAEMON_DIR} && "
        f"cat > {POOL_PNG}.tmp && mv {POOL_PNG}.tmp {POOL_PNG} && "
        f"printf '%s' '{meta}' > {POOL_META}.tmp && mv {POOL_META}.tmp {POOL_META} && "
        f"echo {rotate} > {FB_ROTATE} && "
        f"{FBINK} -q -W GC16 -f -g 'file={POOL_PNG}'"
    )
    ssh_cmd = [
        "ssh", "-i", str(SSH_KEY),
        "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
        "-p", "2222", SSH_TARGET,
        remote,
    ]
    r = subprocess.run(ssh_cmd, input=png.read_bytes(), capture_output=True, cwd=ROOT)
    ok = r.returncode == 0
    log = (r.stdout + r.stderr).decode("utf-8", "replace").strip()
    if ok:
        log = (f"内容池已更新（{orientation}，fb rotate={rotate}），"
               f"daemon 下一轮按 meta 方向重画同一张图。\n" + log)
    else:
        log = (log + "\n推送失败：检查 Kindle 是否休眠（按电源键）或 Wi-Fi 是否连接；详见 AGENTS.md。")[-4000:]
    return ok, log[-4000:]


_usage_refresh_running = False
_usage_lock = threading.Lock()


def _usage_refresh_impl() -> tuple[bool, str]:
    """生成用量卡 HTML -> 渲染横屏 PNG -> 写设备内容池并立即刷屏。"""
    steps: list[str] = []
    r = subprocess.run([sys.executable, str(ROOT / "usage_card.py"), "-o", str(CARDS / "usage.html")],
                       capture_output=True, text=True, cwd=ROOT, encoding="utf-8", errors="replace")
    if not (CARDS / "usage.html").exists():
        return False, ("usage_card.py 失败：" + (r.stdout + r.stderr)[-1500:])
    steps.append("usage_card.py 生成 OK")
    try:
        png = render_html_to_png((CARDS / "usage.html").read_text(encoding="utf-8"),
                                 OUT / "_usage_refresh.png", "landscape")
        steps.append("渲染 OK")
    except Exception as e:
        return False, f"渲染失败：{e}"
    ok, push_log = push_png_to_device(png, "landscape")
    steps.append("推送 " + ("OK" if ok else "失败"))
    return ok, "\n".join(steps) + "\n" + push_log


def ai_edit_html(html: str, boxes: list, comment: str, orientation: str) -> tuple[bool, str]:
    """Ask the local magpie gateway to rewrite the card per annotations."""
    width, height = ORIENTATIONS[orientation]
    desc = "\n".join(
        f"- 圈注{i + 1}: x={b['x']}, y={b['y']}, w={b['w']}, h={b['h']}（像素，基于 {width}×{height}）"
        for i, b in enumerate(boxes)
    )
    user = (
        f"圈注区域：\n{desc}\n\n"
        f"修改要求：{comment}\n\n"
        f"当前 HTML：\n{html}"
    )
    payload = json.dumps({
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": ai_system_prompt(width, height)},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }).encode("utf-8")
    req = urllib.request.Request(MAGPIE, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=AI_TIMEOUT) as resp:
        d = json.loads(resp.read().decode("utf-8"))
    text = d["choices"][0]["message"]["content"].strip()
    # strip accidental markdown fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    text = text.strip()
    if "<html" not in text.lower():
        return False, f"AI 返回内容不像 HTML（前 200 字）：{text[:200]}"
    return True, text


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quiet
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, ctype: str):
        try:
            body = path.read_bytes()
        except OSError:
            self._json({"ok": False, "error": f"not found: {path.name}"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")  # 迭代期禁缓存，改完刷新即生效
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length", 0))
        if n <= 0:
            return {}
        return json.loads(self.rfile.read(n).decode("utf-8"))

    # ---------- GET ----------
    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            self._file(STUDIO / "index.html", "text/html; charset=utf-8")
        elif u.path.startswith("/vendor/"):
            f = (STUDIO / u.path.lstrip("/")).resolve()
            if not str(f).startswith(str((STUDIO / "vendor").resolve())) or not f.exists():
                self._json({"ok": False, "error": "not found"}, 404)
                return
            ctype = {"js": "application/javascript", "css": "text/css",
                     "woff2": "font/woff2", "woff": "font/woff",
                     "ttf": "font/ttf", "otf": "font/otf",
                     "png": "image/png", "svg": "image/svg+xml",
                     }.get(f.suffix.lstrip("."), "text/plain")
            self._file(f, ctype)
        elif u.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        elif u.path == "/api/cards":
            cards = card_store.list_cards()
            self._json({"ok": True, "cards": cards})
        elif u.path == "/api/card":
            qs = parse_qs(u.query)
            name = qs.get("name", [""])[0]
            ver = qs.get("version", [None])[0]
            hit = card_store.read(name, ver)
            if hit is None:
                self._json({"ok": False, "error": f"not found: {name}" + (f"@{ver}" if ver else "")}, 404)
                return
            self._json({"ok": True, "name": name, "version": hit["version"], "html": hit["html"]})
        elif u.path == "/api/card/versions":
            name = parse_qs(u.query).get("name", [""])[0]
            self._json({"ok": True, "name": name, "versions": card_store.versions(name)})
        elif u.path == "/api/usage":
            r = subprocess.run([sys.executable, str(ROOT / "usage_card.py"), "-o", str(CARDS / "usage.html")],
                               capture_output=True, text=True, cwd=ROOT, encoding="utf-8", errors="replace")
            if (CARDS / "usage.html").exists():
                card_store.snapshot("usage.html", note="usage 生成")
                html = (CARDS / "usage.html").read_text(encoding="utf-8")
                self._json({"ok": True, "html": html, "gen_log": (r.stdout + r.stderr)[-2000:]})
            else:
                self._json({"ok": False, "error": (r.stdout + r.stderr)[-2000:] or "usage_card.py produced nothing"}, 500)
        elif u.path == "/api/usage/refresh":
            # 第三期：现场跑 usage_card.py（取 ccusage 数据）→ 渲染横屏 PNG → 推设备内容池。
            # 同一时刻只允许一个刷新（ccusage 全量加载要 20-60s）。
            global _usage_refresh_running
            with _usage_lock:
                if _usage_refresh_running:
                    self._json({"ok": False, "error": "上一次用量卡刷新还在跑，稍等"}, 409)
                    return
                _usage_refresh_running = True
            try:
                ok, log = _usage_refresh_impl()
                self._json({"ok": ok, "log": log} if ok else {"ok": False, "error": log})
            finally:
                with _usage_lock:
                    _usage_refresh_running = False
        elif u.path == "/api/agent-task":
            # 圈注派单队列：页面 POST 落单，本地 Claude 会话领取（GET /api/agent-task/claim）
            # 或按 id 查结果。任务文件放 studio/agent_tasks/，HTML 大文件落盘不进内存队列。
            qs = parse_qs(u.query)
            if "until" in qs:  # 页面查结果
                tid = qs["until"][0]
                f = TASKS / f"{tid}.result.json"
                if f.exists():
                    d = json.loads(f.read_text(encoding="utf-8"))
                    self._json({"ok": True, "status": "done", "html": d.get("html", "")})
                elif (TASKS / f"{tid}.json").exists():
                    self._json({"ok": True, "status": "pending"})
                else:
                    self._json({"ok": False, "error": "任务不存在"}, 404)
            elif "claim" in qs:  # 本地会话领取最老的 pending 单
                pend = sorted(TASKS.glob("*.json"),
                              key=lambda p: p.stat().st_mtime)
                pend = [p for p in pend if not p.name.endswith(".result.json")
                        and not (TASKS / (p.stem + ".result.json")).exists()]
                if not pend:
                    self._json({"ok": True, "task": None})
                    return
                f = pend[0]
                d = json.loads(f.read_text(encoding="utf-8"))
                self._json({"ok": True, "task": {"id": f.stem, **d}})
            else:
                self._json({"ok": False, "error": "need ?until=<id> or ?claim=1"}, 400)
        else:
            self._json({"ok": False, "error": "no route"}, 404)

    # ---------- POST ----------
    def do_POST(self):
        u = urlparse(self.path)
        try:
            data = self._body()
        except Exception as e:
            self._json({"ok": False, "error": f"bad json: {e}"}, 400)
            return
        html = data.get("html", "")
        orientation = data.get("orientation", DEFAULT_ORIENTATION)
        if orientation not in ORIENTATIONS:
            self._json({"ok": False,
                        "error": f"orientation 只支持 {'/'.join(ORIENTATIONS)}"}, 400)
            return
        if u.path == "/api/render":
            if not html.strip():
                self._json({"ok": False, "error": "empty html"}, 400)
                return
            try:
                png = render_html_to_png(html, OUT / "_studio_preview.png", orientation)
                w, h = ORIENTATIONS[orientation]
                b64 = base64.b64encode(png.read_bytes()).decode("ascii")
                self._json({"ok": True, "png": b64, "bytes": png.stat().st_size,
                            "width": w, "height": h, "orientation": orientation})
            except Exception as e:
                self._json({"ok": False, "error": str(e)[-2000:]}, 500)
        elif u.path == "/api/push":
            if not html.strip():
                self._json({"ok": False, "error": "empty html"}, 400)
                return
            try:
                png = render_html_to_png(html, OUT / "_studio_push.png", orientation)
            except Exception as e:
                self._json({"ok": False, "error": f"render failed: {e}"[-2000:]}, 500)
                return
            ok, log = push_png_to_device(png, orientation)
            self._json({"ok": ok, "log": log})
        elif u.path == "/api/ai-edit":
            if not html.strip() or not data.get("comment", "").strip():
                self._json({"ok": False, "error": "需要 html 和 comment"}, 400)
                return
            boxes = [b for b in data.get("boxes", []) if all(k in b for k in ("x", "y", "w", "h"))]
            try:
                ok, out = ai_edit_html(html, boxes, data["comment"].strip(), orientation)
                self._json({"ok": ok, "html": out} if ok else {"ok": False, "error": out})
            except Exception as e:
                self._json({"ok": False, "error": f"AI 网关调用失败：{e}"[-1500:]}, 502)
        elif u.path == "/api/agent-task":
            # 圈注落单：页面把当前 HTML + 圈注 + 要求投进队列，本地 Claude 会话来领
            import time
            if not html.strip() or not data.get("comment", "").strip():
                self._json({"ok": False, "error": "需要 html 和 comment"}, 400)
                return
            TASKS.mkdir(exist_ok=True)
            tid = time.strftime("%H%M%S") + f"-{int(time.time() * 1000) % 1000:03d}"
            task = {
                "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                "orientation": orientation,
                "boxes": data.get("boxes", []),
                "comment": data["comment"].strip(),
                "card": data.get("card", ""),  # 关联的卡片名；回填时按它存版本
                "html": html,
            }
            (TASKS / f"{tid}.json").write_text(json.dumps(task, ensure_ascii=False),
                                               encoding="utf-8", newline="\n")
            self._json({"ok": True, "id": tid})
        elif u.path == "/api/agent-result":
            # 本地会话回填结果：POST {id, html, save_as?}
            # save_as 给了就把结果存进卡片库（旧版自动存档），页面轮询时一并拿到新内容
            tid = data.get("id", "")
            out_html = data.get("html", "")
            if not tid or not (TASKS / f"{tid}.json").exists():
                self._json({"ok": False, "error": "任务不存在"}, 404)
                return
            if not out_html.strip():
                self._json({"ok": False, "error": "html 为空"}, 400)
                return
            TASKS.mkdir(exist_ok=True)
            saved_as = ""
            save_as = data.get("save_as", "")
            if save_as and save_as.endswith(".html") and "/" not in save_as and "\\" not in save_as:
                try:
                    card_store.save(save_as, out_html, note=f"AI 回填（任务 {tid}）")
                    saved_as = save_as
                except ValueError:
                    pass
            (TASKS / f"{tid}.result.json").write_text(
                json.dumps({"html": out_html, "saved_as": saved_as}, ensure_ascii=False),
                encoding="utf-8", newline="\n")
            self._json({"ok": True, "saved_as": saved_as})
        elif u.path == "/api/card/save":
            # 编辑器内容落盘（旧版自动存档）。POST {name, html, note?}
            name = data.get("name", "")
            if not html.strip():
                self._json({"ok": False, "error": "html 为空"}, 400)
                return
            try:
                prev = card_store.save(name, html, note=data.get("note", "编辑器保存"))
            except ValueError as e:
                self._json({"ok": False, "error": str(e)}, 400)
                return
            self._json({"ok": True, "prev_version": prev})
        elif u.path == "/api/card/new":
            # 新建空白卡片：标准 1264×1680 模板。POST {name}
            import time as _t
            name = data.get("name", "").strip()
            if not name:
                self._json({"ok": False, "error": "需要 name"}, 400)
                return
            if not name.endswith(".html"):
                name += ".html"
            if "/" in name or "\\" in name:
                self._json({"ok": False, "error": "名字不能带路径"}, 400)
                return
            f = CARDS / name
            if f.exists():
                self._json({"ok": False, "error": f"{name} 已存在"}, 409)
                return
            tpl = (
                "<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"utf-8\">\n<style>\n"
                "  * { margin: 0; padding: 0; box-sizing: border-box; }\n"
                "  body { width: 1264px; height: 1680px; background: #fff; color: #000;\n"
                "         font-family: 'Microsoft YaHei', sans-serif; padding: 80px; }\n"
                "  h1 { font-size: 88px; margin-bottom: 40px; }\n"
                "  p { font-size: 36px; line-height: 1.6; }\n"
                "</style>\n</head>\n<body>\n"
                f"  <h1>{_t.strftime('%Y-%m-%d')}</h1>\n"
                "  <p>在这里写内容。约束：无 flex gap / position:fixed / 动画；字号 ≥30px。</p>\n"
                "</body>\n</html>\n"
            )
            f.write_text(tpl, encoding="utf-8", newline="\n")
            self._json({"ok": True, "name": name})
        else:
            self._json({"ok": False, "error": "no route"}, 404)


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"kindle-studio -> http://127.0.0.1:{PORT}  (Ctrl+C 停止)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
