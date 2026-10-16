# -*- coding: utf-8 -*-
"""usage_card.py - 从 ccusage 取本地 AI CLI 用量，渲染 1264x1680 墨水屏用量卡。

用法:
    python usage_card.py -o cards/usage.html
    python usage_card.py -o cards/usage.html --json out/usage-dump.json
    python usage_card.py -o cards/usage.html --demo

数据源优先级: --json 文件 > 现场跑 ccusage > 内嵌 sample（卡面标 DEMO）。
--json 接受合并 dump: {"daily":[], "weekly":[], "monthly":[], "blocks":[]}，键任选。
"""

import argparse
import datetime as dt
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

WIDTH = 1264
HEIGHT = 1680
CCUSAGE_TIMEOUT = 300

AGENT_NAMES = {
    "claude": "Claude Code",
    "codex": "Codex CLI",
    "gemini": "Gemini CLI",
    "antigravity": "Antigravity",
    "grok": "Grok CLI",
    "zcode": "ZCode",
    "hermes": "Hermes",
    "droid": "Droid",
    "opencode": "OpenCode",
    "amp": "Amp",
    "copilot": "Copilot CLI",
    "kimi": "Kimi CLI",
    "qwen": "Qwen Code",
    "goose": "Goose",
    "kilo": "Kilo Code",
    "codebuff": "Codebuff",
    "openclaw": "OpenClaw",
    "pi": "Pi",
}


# ---------------------------------------------------------------- 数据获取

def find_npx():
    for name in ("npx.cmd", "npx", "npx.exe"):
        p = shutil.which(name)
        if p:
            return p
    for name in ("bunx.cmd", "bunx"):
        p = shutil.which(name)
        if p:
            return p
    return None


def run_ccusage(args):
    exe = find_npx()
    if exe is None:
        raise RuntimeError("npx/bunx not found on PATH")
    cmd = [exe, "--yes", "ccusage@latest"] + args
    r = subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=CCUSAGE_TIMEOUT,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ccusage rc={r.returncode}: {r.stderr.strip()[-300:]}")
    return json.loads(r.stdout)


def fetch_live(today):
    since = min(today.replace(day=1), today - dt.timedelta(days=today.weekday()))
    sections = run_ccusage([
        "daily", "--json", "--by-agent",
        "--sections", "daily,weekly,monthly",
        "--since", since.strftime("%Y%m%d"),
    ])
    try:
        blocks = run_ccusage(["blocks", "--json", "--active"])
    except Exception as e:  # blocks 失败不致命，只省略窗口板块
        print(f"warn: blocks failed, omit window section: {e}", file=sys.stderr)
        blocks = {}
    sections["blocks"] = blocks.get("blocks")
    return sections


def load_data(json_path, demo):
    if demo:
        return dict(SAMPLE), True
    if json_path is not None:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(f"{json_path}: top level must be an object")
        return data, False
    today = dt.date.today()
    try:
        data = fetch_live(today)
    except Exception as e:
        print(f"warn: ccusage failed ({e}), falling back to sample", file=sys.stderr)
        return dict(SAMPLE), True
    if not data.get("daily"):
        print("warn: ccusage returned no daily rows, falling back to sample", file=sys.stderr)
        return dict(SAMPLE), True
    return data, False


# ---------------------------------------------------------------- 数据整形

def pick_row(rows, today, kind):
    """从 rows 里挑覆盖今天的行；没有就退回最后一行，再没有返回 None。"""
    if not rows:
        return None
    if kind == "daily":
        want = today.isoformat()
        for r in rows:
            if r.get("period") == want:
                return r
        return None  # 今天没有用量 => 今日板块整块省略
    if kind == "weekly":
        for r in rows:
            try:
                start = dt.date.fromisoformat(r.get("period", ""))
            except ValueError:
                continue
            if start <= today <= start + dt.timedelta(days=6):
                return r
    if kind == "monthly":
        want = today.strftime("%Y-%m")
        for r in rows:
            if r.get("period") == want:
                return r
    return rows[-1]


def agent_map(row):
    return {a.get("agent"): a for a in (row or {}).get("agents", []) if a.get("agent")}


def fmt_tokens(n):
    n = int(n or 0)
    if n >= 100_000_000:
        return f"{n / 100_000_000:.2f} 亿"
    if n >= 10_000:
        return f"{n / 10_000:.1f} 万"
    return f"{n:,}"


def fmt_cost(c):
    return f"${float(c or 0):,.2f}"


def parse_local(s):
    try:
        return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone()
    except ValueError:
        return None


# ---------------------------------------------------------------- HTML

CSS = """
  * { margin: 0; padding: 0; }
  body {
    width: 1264px; height: 1680px;
    font-family: "Noto Serif SC", "SimSun", serif;
    background: #fff; color: #111;
    padding: 84px 96px 56px;
    box-sizing: border-box;
  }
  table { border-collapse: collapse; }
  .head { width: 100%; }
  .tag { font-family: "JetBrains Mono", monospace; font-size: 27px; letter-spacing: 7px; color: #6b6355; }
  .demo { display: inline-block; font-size: 32px; font-weight: bold;
    letter-spacing: 6px; border: 4px solid #111; padding: 5px 18px; }
  h1 { font-family: "Anthropic Sans", "Inter", sans-serif;
       font-size: 84px; line-height: 1.08; margin: 18px 0 30px; letter-spacing: .01em; }
  .rule { height: 5px; background: #111; margin-bottom: 44px; }
  .sec { margin-bottom: 40px; }
  .sec-title { font-family: "Noto Sans SC", sans-serif; font-size: 29px; font-weight: bold;
    letter-spacing: 4px; color: #111;
    border-bottom: 2px solid #111; padding-bottom: 10px; margin-bottom: 18px; }
  .big { font-family: "JetBrains Mono", monospace; font-size: 72px; font-weight: bold; line-height: 1.12; }
  .big .unit { font-family: "JetBrains Mono", monospace; font-size: 30px; font-weight: normal; color: #55503f; }
  .sub { font-family: "Noto Serif SC", serif; font-weight: 500; font-size: 33px; color: #3a352a; margin-top: 8px; }
    .num { font-family: "JetBrains Mono", monospace; }
  .duo { width: 100%; }
  .duo td { vertical-align: top; }
  .duo td.r { padding-left: 72px; }
  .duo .label { font-family: "Noto Serif SC", serif; font-weight: 500; font-size: 29px; color: #55503f; margin-bottom: 6px; }
  .duo .big { font-size: 56px; }
  .landscape .duo .big { font-size: 44px; }
  .grid { width: 100%; font-size: 33px; }
  .grid td { font-weight: 500; }
  .grid th { font-family: "Noto Sans SC", sans-serif; text-align: left; font-size: 28px; font-weight: normal;
    color: #6b6355; border-bottom: 2px solid #111; padding: 8px 0; letter-spacing: 1px; }
  .grid td { padding: 12px 0; border-bottom: 1px solid #d8d2c4; }
  .grid tr:last-child td { border-bottom: none; }
  .grid .r { text-align: right; }
  .grid td.r { font-variant-numeric: tabular-nums; }
  .track { height: 40px; background: #ece8de; margin: 14px 0 14px; }
  .fill { height: 40px; background: #111; }
  .foot { font-family: "Noto Serif SC", serif; font-weight: 500; margin-top: 10px; font-size: 28px; color: #6b6355; line-height: 1.6; }
"""




def esc(s):
    return html.escape(str(s), quote=True)


def latin_wrap(escaped: str) -> str:
    """把数字/英文片段包进 .num（JetBrains Mono），中文留在思源宋体。入参须已 esc。"""
    escaped = re.sub(r"([\d][\d,.:%$]*|[A-Za-z][A-Za-z0-9-]*)", r'<span class="num">\1</span>', escaped)
    return escaped


def sec_title(text):
    return f'<div class="sec-title">{esc(text)}</div>'


def sec_today(row):
    if not row:
        return ""
    line = f"费用 {fmt_cost(row.get('totalCost'))}  ·  输出 {fmt_tokens(row.get('outputTokens'))} tokens"
    body = [
        f'<div class="big">{latin_wrap(esc(fmt_tokens(row.get("totalTokens"))))}<span class="unit"> tokens</span></div>',
        f'<div class="sub">{latin_wrap(esc(line))}</div>',
    ]
    return f'<div class="sec">{sec_title("今日")}' + "".join(body) + "</div>"


def sec_period(row, label):
    if not row:
        return ""
    return (
        f'<div class="label">{esc(label)}</div>'
        f'<div class="big">{esc(fmt_tokens(row.get("totalTokens")))}</div>'
        f'<div class="sub">{latin_wrap(esc(fmt_cost(row.get("totalCost"))))}</div>'
    )


def sec_week_month(week_row, month_row):
    if not week_row and not month_row:
        return ""
    cells = [
        f'<td>{sec_period(week_row, "本周 tokens")}</td>',
        f'<td class="r">{sec_period(month_row, "本月 tokens")}</td>',
    ]
    labels = [n for n, r in (("本周", week_row), ("本月", month_row)) if r]
    inner = "".join(c for c, r in zip(cells, (week_row, month_row)) if r)
    return f'<div class="sec">{sec_title(" / ".join(labels))}<table class="duo"><tr>{inner}</tr></table></div>'


def sec_block(block):
    if not block:
        return ""
    start, end = parse_local(block.get("startTime")), parse_local(block.get("endTime"))
    proj = block.get("projection") or {}
    line1 = []
    if start and end:
        line1.append(f"时段 {start:%H:%M} - {end:%H:%M}")
    if proj.get("remainingMinutes") is not None:
        line1.append(f"剩余 {int(proj['remainingMinutes'])} 分钟")
    body = []
    pct = None
    total = proj.get("totalTokens")
    if total:
        pct = max(0, min(100, round(int(block.get("totalTokens") or 0) / int(total) * 100)))
        body.append(f'<div class="track"><div class="fill" style="width:{pct}%"></div></div>')
    line2 = f"tokens {fmt_tokens(block.get('totalTokens'))}  ·  费用 {fmt_cost(block.get('costUSD'))}"
    if pct is not None:
        line2 += f"  ·  进度 {pct}%"
    if line1:
        body.append(f'<div class="sub">{esc("  ·  ".join(line1))}</div>')
    body.append(f'<div class="sub">{latin_wrap(esc(line2))}</div>')
    return f'<div class="sec">{sec_title("当前 5 小时窗口")}' + "".join(body) + "</div>"


def sec_agents(today_map, month_map):
    ids = set(today_map) | set(month_map)
    if not ids:
        return ""
    def sort_key(aid):
        m = month_map.get(aid) or {}
        t = today_map.get(aid) or {}
        return (-(m.get("totalCost") or 0), -(t.get("totalTokens") or 0), aid)
    rows = ['<tr><th>CLI</th><th class="r">今日 tokens</th><th class="r">今日费用</th><th class="r">本月费用</th></tr>']
    for aid in sorted(ids, key=sort_key):
        t = today_map.get(aid) or {}
        m = month_map.get(aid) or {}
        name = AGENT_NAMES.get(aid, aid.capitalize())
        today_tok = fmt_tokens(t["totalTokens"]) if t.get("totalTokens") is not None else "-"
        today_cost = fmt_cost(t["totalCost"]) if t.get("totalCost") is not None else "-"
        month_cost = fmt_cost(m["totalCost"]) if m.get("totalCost") is not None else "-"
        rows.append(
            f"<tr><td>{latin_wrap(esc(name))}</td>"
            f'<td class="r">{latin_wrap(esc(today_tok))}</td>'
            f'<td class="r">{latin_wrap(esc(today_cost))}</td>'
            f'<td class="r">{latin_wrap(esc(month_cost))}</td></tr>'
        )
    return f'<div class="sec">{sec_title("各 CLI 用量")}<table class="grid">{"".join(rows)}</table></div>'


def render(data, demo, source_note, today, orientation="portrait"):
    today_row = pick_row(data.get("daily"), today, "daily")
    week_row = pick_row(data.get("weekly"), today, "weekly")
    month_row = pick_row(data.get("monthly"), today, "monthly")
    block = next((b for b in (data.get("blocks") or []) if b.get("isActive")), None)

    tag = f"KINDLE GADGET / USAGE / {today.isoformat()}"
    badge = '<td class="r" style="vertical-align:top"><span class="demo">DEMO</span></td>' if demo else ""
    secs = [
        sec_today(today_row),
        sec_week_month(week_row, month_row),
        sec_block(block),
        sec_agents(agent_map(today_row), agent_map(month_row)),
    ]
    body_css = CSS
    if orientation == "landscape":
        # 横屏 1680×1264：内容排两列网格（今日+窗口 | 周/月+CLI 表），字号整体收紧
        body_css = CSS.replace("width: 1264px; height: 1680px;", "width: 1680px; height: 1264px;")
        body_css += """
  body { padding: 56px 72px 40px; }
  h1 { font-size: 64px; margin: 12px 0 20px; }
  .rule { margin-bottom: 26px; }
  .sec { margin-bottom: 24px; }
  .cols { display: table; width: 100%; }
  .col { display: table-cell; vertical-align: top; width: 50%; }
  .col.l { padding-right: 40px; }
  .col.r { padding-left: 40px; border-left: 2px solid #111; }
  .big { font-size: 54px; }
  .duo .big { font-size: 44px; }
  .grid { font-size: 27px; }
  .grid td { padding: 9px 0; }
  .track { height: 30px; margin: 10px 0; }
  .fill { height: 30px; }
  .foot { margin-top: 4px; font-size: 24px; }
"""
        left = "".join(secs[:2])
        right = "".join(secs[2:])
        content = f'<div class="cols"><div class="col l">{left}</div><div class="col r">{right}</div></div>'
    else:
        content = "".join(secs)
    parts = [
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        "<head>",
        '<meta charset="utf-8">',
        f"<style>{body_css}</style>",
        "</head>",
        "<body>",
        f'<table class="head"><tr><td><div class="tag">{esc(tag)}</div>'
        f"<h1>YOLO Usage</h1></td>{badge}</tr></table>",
        '<div class="rule"></div>',
        content,
        f'<div class="foot">{latin_wrap(esc(source_note))}<br>生成时间 {latin_wrap(dt.datetime.now().strftime("%Y-%m-%d %H:%M"))}</div>',
        "</body>",
        "</html>",
        "",
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------- sample

def _sample_block():
    start = dt.datetime.now().replace(minute=0, second=0, microsecond=0) - dt.timedelta(hours=2)
    end = start + dt.timedelta(hours=5)
    return {
        "isActive": True,
        "startTime": start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "endTime": end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "totalTokens": 87_601_864,
        "costUSD": 20.78,
        "projection": {"totalTokens": 116_000_000, "totalCost": 27.5, "remainingMinutes": 168},
    }


SAMPLE = {
    "daily": [{
        "period": dt.date.today().isoformat(),
        "agent": "all",
        "totalTokens": 118_607_065,
        "outputTokens": 1_185_672,
        "totalCost": 47.53,
        "agents": [
            {"agent": "claude", "totalTokens": 88_013_016, "totalCost": 20.96},
            {"agent": "codex", "totalTokens": 29_752_582, "totalCost": 21.22},
            {"agent": "gemini", "totalTokens": 841_467, "totalCost": 5.35},
        ],
    }],
    "weekly": [{
        "period": (dt.date.today() - dt.timedelta(days=dt.date.today().weekday())).isoformat(),
        "agent": "all",
        "totalTokens": 2_437_653_015,
        "totalCost": 403.44,
    }],
    "monthly": [{
        "period": dt.date.today().strftime("%Y-%m"),
        "agent": "all",
        "totalTokens": 7_742_282_398,
        "totalCost": 1_573.4,
    }],
    "blocks": [_sample_block()],
}


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="render ccusage usage card (1264x1680)")
    ap.add_argument("-o", "--out", type=Path, default=Path("cards/usage.html"))
    ap.add_argument("--json", type=Path, default=None,
                    help="ccusage 合并 dump 文件（daily/weekly/monthly/blocks 任选）")
    ap.add_argument("--demo", action="store_true", help="强制使用内嵌 sample 数据")
    ap.add_argument("--orientation", choices=["portrait", "landscape"], default="portrait",
                    help="竖屏 1264x1680（默认）/ 横屏 1680x1264（两列布局）")
    a = ap.parse_args()
    if a.json is not None and a.demo:
        ap.error("--json and --demo are mutually exclusive")

    data, demo = load_data(a.json, a.demo)

    if demo:
        source_note = "数据源：内嵌示例（DEMO），非真实用量"
    elif a.json is not None:
        source_note = f"数据源：{a.json.name}（ccusage dump）"
    else:
        source_note = "数据源：ccusage 现场采集"

    html_text = render(data, demo, source_note, dt.date.today(), a.orientation)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(html_text, encoding="utf-8", newline="\n")
    print(f"{a.out}  demo={demo}  bytes={a.out.stat().st_size}")


if __name__ == "__main__":
    main()
