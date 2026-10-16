# kindle-gadget · 把越狱 Kindle 变成 agent 推送的墨水屏看板

> English below / 英文说明在下半部分。

一台越狱 Kindle Oasis 3，变成桌面上常驻的 7 英寸 300ppi 墨水屏看板：任意 agent（claude / codex / grok / omp …）产出一段 HTML 或一张 PNG，一条命令推上屏幕，约 2 秒出图。渲染、排版、灰度抖动全部在 PC 侧完成，设备保持"愚蠢"，只负责刷屏。

```bash
python push.py cards/hello.html          # 全刷上屏（GC16，黑闪一次）
python push.py cards/hello.html --partial  # 局部刷新，无黑闪
python daemon/kd.py start                # 常驻看板 daemon（60s 轮询、原子推送）
python studio/tray.py                    # 网页工作台 + 系统托盘（127.0.0.1:8762）
```

## 能做什么

- **渲染链**：HTML → Chrome headless 截图 → Pillow 16 阶灰度 Floyd–Steinberg 抖动 → SSH 管道 → FBInk 刷屏。中文、复杂排版零障碍（PC 渲染），横竖屏都支持
- **看板 daemon**：设备侧 busybox ash 常驻循环，GL16 局刷 + 周期性 GC16 全清残影；PC 侧 `kd.py` 控制
- **开机自启**：走 SpiderCat 官方 boot 钩子，重启后 telnetd / dropbear / iptables / daemon 全部自动恢复，零 rootfs 写入
- **Studio 工作台**：本地网页（只绑 127.0.0.1）——卡片 HTML 编辑、真实渲染预览（带 Oasis 设备壳）、圈注改稿（发给本地 Agent 领单处理）、版本管理、深浅主题、托盘一键切模式
- **用量卡**：`usage_card.py` 从 ccusage 取本机 AI CLI 用量（tokens / 费用 / 5 小时窗口），渲染成墨水屏卡片

## 文档（面向 agent，照着跑就能复现）

| 文档 | 内容 |
|---|---|
| [docs/opensource/JAILBREAK.zh.md](docs/opensource/JAILBREAK.zh.md) | 越狱：机型/固件判定、方案选型、SpiderCat 全步骤、红线、踩坑实录 |
| [docs/opensource/SETUP.zh.md](docs/opensource/SETUP.zh.md) | 越狱后配置：SSH/telnet、KOReader、渲染链、daemon、自启、Studio，每步含验证命令 |
| [docs/opensource/INDEX.md](docs/opensource/INDEX.md) | 文档导航 + 已验证/未验证/实测失败清单 |
| [AGENTS.md](AGENTS.md) | 设备事实与坑的权威来源（本仓库的维护者备忘） |
| [push.md](push.md) | push.py 的 agent 调用契约 |

English versions live next to the Chinese ones (`JAILBREAK.en.md` / `SETUP.en.md`).

## 边界，先说清

- 实测机型只有一台：**Kindle Oasis 3（第 10 代）+ 固件 5.18.2 + SpiderCat jb.sh v2.2.1 + Windows PC**。其他机型/固件/操作系统的完整清单见 [INDEX.md](docs/opensource/INDEX.md)，未验证的部分全部明说
- 越狱是非官方修改，有变砖与失去保修风险；本教程只写 userstore，不碰 rootfs，但请自担风险
- 设备 IP 等示例值可用环境变量 `KINDLE_HOST` 覆盖；本仓库不含任何真实序列号、MAC、密钥

## License

MIT，见 [LICENSE](LICENSE)。第三方组件：CodeMirror（MIT）、Inter（OFL）、FBInk / KOReader / SpiderCat 归各自作者所有。

---

# kindle-gadget · Turn a jailbroken Kindle into an agent-driven e-ink dashboard

A jailbroken Kindle Oasis 3 becomes an always-on 7" 300ppi e-ink dashboard: any agent (claude / codex / grok / omp …) emits an HTML file or a PNG, one command puts it on the screen in about two seconds. Rendering, typography and grayscale dithering all happen on the PC; the device stays dumb and only refreshes the display.

```bash
python push.py cards/hello.html            # full refresh (GC16, one black flash)
python push.py cards/hello.html --partial  # partial refresh, no flash
python daemon/kd.py start                  # resident dashboard daemon (60s polling, atomic push)
python studio/tray.py                      # web workbench + tray (127.0.0.1:8762)
```

## Highlights

- **Render chain**: HTML -> headless Chrome screenshot -> Pillow 16-level Floyd–Steinberg dithering -> SSH pipe -> FBInk. CJK and complex layouts render on the PC; portrait and landscape both supported.
- **Dashboard daemon**: a busybox ash loop on the device (GL16 partial refresh, periodic GC16 full refresh); `kd.py` on the PC controls it.
- **Autostart**: uses SpiderCat's official boot hook — after a reboot, telnetd / dropbear / iptables / the daemon all come back on their own, zero rootfs writes.
- **Studio workbench**: a local web app (binds 127.0.0.1 only) — card editing, true-render preview with an Oasis device shell, annotate-and-rewrite via your local agent, version history, light/dark themes, tray mode switching.
- **Usage card**: `usage_card.py` renders your local AI-CLI usage (tokens / cost / 5-hour window via ccusage) as an e-ink card.

## Docs (written for agents to follow end-to-end)

| Doc | Contents |
|---|---|
| [JAILBREAK.en.md](docs/opensource/JAILBREAK.en.md) | jailbreak: model/firmware ID, method matrix, full SpiderCat walkthrough, red lines, pitfall log |
| [SETUP.en.md](docs/opensource/SETUP.en.md) | post-jailbreak setup: SSH/telnet, KOReader, render chain, daemon, autostart, Studio — each step with a verification command |
| [INDEX.md](docs/opensource/INDEX.md) | navigation + verified / unverified / known-broken lists |
| [AGENTS.md](AGENTS.md) | authoritative device facts and pitfalls (maintainer notes) |
| [push.md](push.md) | agent-facing push.py contract |

## Scope, stated up front

- Verified on exactly one device: **Kindle Oasis 3 (10th gen) + firmware 5.18.2 + SpiderCat jb.sh v2.2.1 + a Windows PC**. Everything unverified is listed explicitly in [INDEX.md](docs/opensource/INDEX.md).
- Jailbreaking is an unofficial modification with brick and warranty risks; this guide only writes to the userstore, never rootfs — still, you proceed at your own risk.
- Example values (device IP etc.) can be overridden via the `KINDLE_HOST` environment variable; the repo contains no real serials, MACs or keys.

## License

MIT, see [LICENSE](LICENSE). Third-party components: CodeMirror (MIT), Inter (OFL); FBInk / KOReader / SpiderCat belong to their respective authors.
