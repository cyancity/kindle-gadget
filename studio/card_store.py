"""卡片版本化存储。

布局：
  cards/<name>.html            当前版（渲染/推送/编辑器用的就是它）
  cards/versions/<name>/<ts>.html  历史版本（ts=YYYYMMDD-HHMMSS）
  cards/versions/<name>/meta.json  版本注记 [{version, note, bytes}]

写 current 前先 snapshot()：把改动前的 current 存档一份，任何来源的修改
（编辑器保存、AI 回填、usage 生成）都有版本可回滚。
"""
import json
import time
from pathlib import Path

CARDS = Path(__file__).resolve().parent.parent / "cards"
VERSIONS = CARDS / "versions"


def _safe(name: str) -> bool:
    return bool(name) and "/" not in name and "\\" not in name and name.endswith(".html")


def snapshot(name: str, note: str = "") -> str | None:
    """把当前 current.html 存进 versions/，返回版本号；无 current 时返回 None。"""
    if not _safe(name):
        return None
    cur = CARDS / name
    if not cur.exists():
        return None
    vdir = VERSIONS / cur.stem
    vdir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    dest = vdir / f"{ts}.html"
    if dest.exists():  # 同秒多次：加序号
        i = 1
        while dest.exists():
            dest = vdir / f"{ts}-{i}.html"
            i += 1
        ts = dest.stem
    dest.write_text(cur.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    meta_path = vdir / "meta.json"
    meta = []
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta = []
    meta.append({"version": ts, "note": note, "bytes": dest.stat().st_size})
    meta_path.write_text(json.dumps(meta[-200:], ensure_ascii=False, indent=1),
                         encoding="utf-8", newline="\n")
    return ts


def save(name: str, html: str, note: str = "") -> str | None:
    """写入新内容：先存档旧版，再落 current。返回旧版本号（首写返回 None）。"""
    if not _safe(name):
        raise ValueError(f"bad card name: {name}")
    prev = snapshot(name, note=f"改动前存档：{note}" if note else "改动前存档")
    (CARDS / name).write_text(html, encoding="utf-8", newline="\n")
    return prev


def read(name: str, version: str | None = None) -> dict | None:
    if not _safe(name):
        return None
    if version:
        f = VERSIONS / Path(name).stem / f"{version}.html"
        if not f.exists():
            return None
        return {"version": version, "html": f.read_text(encoding="utf-8")}
    cur = CARDS / name
    if not cur.exists():
        return None
    vs = versions(name)
    return {"version": vs[-1]["version"] if vs else "current", "html": cur.read_text(encoding="utf-8")}


def versions(name: str) -> list:
    if not _safe(name):
        return []
    meta_path = VERSIONS / Path(name).stem / "meta.json"
    if not meta_path.exists():
        return []
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return []


def list_cards() -> list[dict]:
    """[{name, bytes, versions: n, last_note}]，按名字排序。"""
    out = []
    for p in sorted(CARDS.glob("*.html")):
        vs = versions(p.name)
        out.append({
            "name": p.name,
            "bytes": p.stat().st_size,
            "version_count": len(vs),
            "last_note": vs[-1]["note"] if vs else "",
        })
    return out
