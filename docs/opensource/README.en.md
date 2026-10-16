# kindle-gadget: Turn a jailbroken Kindle into an agent-driven e-ink dashboard

> **Scope**: the whole toolchain was verified on one device: Kindle Oasis 3 (10th gen, 2019, CN 8GB Wi-Fi, serial G000WL******) + firmware 5.18.2 + the SpiderCat jailbreak (jb.sh v2.2.1). Other models or firmware versions: reference only. Commands, paths and firmware behavior may differ.
>
> **Disclaimer**: jailbreaking is an unofficial modification. You can brick the device and you lose any remaining warranty, at your own risk. This guide assumes you own the device, it is out of warranty, and you can wipe its data. Nothing here writes to the rootfs (see the red lines in [JAILBREAK.en.md](JAILBREAK.en.md)).

[中文](README.zh.md)

## What it is

A jailbroken Kindle Oasis 3 that acts as an e-ink dashboard on your desk. Any agent in your herd (claude / codex / grok / omp) produces an HTML fragment or a PNG, and one command puts it on the screen:

```bash
python push.py cards/hello.html
```

The content appears on the Kindle about 2 seconds later (GC16 full refresh, one black flash). For small changes use `--partial` for a flash-free partial refresh. While the dashboard daemon is running, a push only writes a file; the daemon picks it up within the next polling round (60 seconds by default).

What you get: a 7-inch 300 ppi e-ink panel, 1264x1680, 16-level grayscale with Floyd-Steinberg dithering. Chinese and complex layouts are rendered on the PC side, so there are no on-device font problems. In AC (plugged-in) mode the device stays awake and checks for new images every minute. The whole chain runs over Wi-Fi (SSH), no cable needed.

## Architecture

```
        PC (Windows / Git Bash)                       Kindle Oasis 3 (jailbroken, root)
+-------------------------------+   SSH :2222    +-----------------------------------+
| agent (herdr / claude / ...)  |                | dropbear (bundled with KOReader,  |
|   |  HTML / PNG               |                |   key-only auth)                  |
|   v                           |  cat | ssh     |   v                               |
| render.py                     |  ----------->  | /mnt/us/qoder/card.png            |
|   Chrome headless screenshot  |  (no sftp/scp, |   |                               |
|   Pillow 16-level gray +      |   pipe files   |   v                               |
|   Floyd-Steinberg dithering   |   over stdin)  | fbink -W GC16 -f -g file=...      |
+-------------------------------+                |   |                               |
                                                 |   v  e-ink framebuffer            |
|  daemon control plane (PC)    |                | 1264x1680, 8bpp grayscale         |
|  python daemon/kd.py push ...  |  ----------->  | /mnt/us/qoder/daemon/dashboard.sh |
|  (atomic tmp+mv of current.png)|               |   60s poll loop, always-on        |
+-------------------------------+                +-----------------------------------+
                                                        ^
                                                        | boot hook
                                                 /etc/upstart/kmc.conf (SpiderCat)
                                                        -> /mnt/us/emergency.sh
                                                        -> /mnt/us/qoder/autostart/autostart.sh
                                                           (telnetd + dropbear + iptables + hooks.d)
```

Four layers:

| Layer | Where | What it does |
|---|---|---|
| Render | PC-side `render.py` | HTML card -> Chrome headless screenshot -> 16-level dithered grayscale PNG. Chinese text and complex layout are solved on the PC; the device stays dumb |
| Push | PC-side `push.py` | Render + `cat \| ssh` pipe transfer + FBInk refresh, one command |
| Dashboard | Device-side `daemon/device/dashboard.sh` | A busybox ash resident loop, one round per 60 s: GL16 partial refresh, a GC16 full refresh every 6 rounds to clear ghosting; controlled from the PC with `daemon/kd.py` and atomic pushes |
| Autostart | Device-side `autostart/` | Uses the official SpiderCat boot hook `/mnt/us/emergency.sh` to restore telnetd / dropbear / iptables on every boot, zero rootfs writes |
| Workbench | PC-side `studio/` | Local web workbench: card editing, true-render preview, annotate-to-agent rewrites, version history, system tray (see [../STUDIO.md](../STUDIO.md)) |

## Quick start

Prerequisites: a Kindle Oasis 3 (other post-2019 Kindle models follow a similar flow but are unverified), a Windows PC (Git Bash + Python 3.10+ + Pillow + Chrome or Edge), and the device and PC on the same Wi-Fi.

1. **Jailbreak**: identify your model and firmware, then follow [JAILBREAK.en.md](JAILBREAK.en.md) to jailbreak with SpiderCat and get root.
2. **Set up channels and tooling**: follow [SETUP.en.md](SETUP.en.md) to bring up SSH, install KOReader/dropbear, and verify the FBInk render chain. Every step lists a verification command and its expected output.
3. **Push your first card**:

   ```bash
   python push.py cards/hello.html           # full refresh (one black flash)
   python push.py cards/hello.html --partial # partial refresh (no flash, for small edits)
   ```

4. **Resident dashboard**:

   ```bash
   python daemon/kd.py start                # deploy + start (idempotent)
   python daemon/kd.py push out/xxx.png     # atomic push, drawn on the next round
   python daemon/kd.py status               # process / config / battery / log
   ```

5. **Autostart** (optional, restores channels after a reboot):

   ```bash
   cd autostart && ./deploy.sh              # deploy emergency.sh + autostart.sh
   ./deploy.sh --status                     # listeners / iptables / log
   ```

6. **Studio web workbench** (optional, local-only at 127.0.0.1:8762): edit card HTML with a true-render preview (Oasis device shell, portrait/landscape), annotate areas for the local agent to rewrite, per-card version history, and a tray icon to switch the Kindle between normal and dashboard modes. Tray needs `pip install pystray`:

   ```bash
   python studio/tray.py        # tray resident; or python studio/server.py for the server only
   ```

7. **Usage card template**: `python usage_card.py -o cards/usage.html` renders your local AI-CLI usage (via ccusage) as a card, then `python push.py cards/usage.html --orientation landscape`. Falls back to a DEMO sample when there is no data.

Minimal agent integration: anything that can produce an HTML/PNG file runs one `python push.py <file>` or `python daemon/kd.py push <png>`. See `push.md` for the agent-facing contract.

## Repository layout

```
kindle-gadget/
+-- README.zh.md / README.en.md    this file
+-- JAILBREAK.zh.md / .en.md       jailbreak guide (model ID, method selection, SpiderCat steps, red lines, pitfalls)
+-- SETUP.zh.md / .en.md           post-jailbreak setup (SSH, KOReader, FBInk chain, daemon, autostart), each step verified
+-- INDEX.md                       doc navigation and the not-yet-verified list
+-- render.py                      HTML -> Chrome headless screenshot -> 16-level grayscale PNG
+-- push.py / push.md              one-command push; push.md is the agent-facing usage contract
+-- telnet_run.py                  minimal telnet client (backup root channel)
+-- rpc.py / tk.py                 early file-RPC / telnet experiments, kept for reference
+-- cards/                         card HTML sources (1264x1680)
+-- out/                           rendered output
+-- daemon/                        dashboard daemon: kd.py (PC control) + device/ (device scripts) + DESIGN.md
+-- autostart/                     boot hook: autostart.sh + emergency.sh + deploy.sh + DESIGN.md
+-- usage_card.py                  ccusage usage-card template (AI CLI usage -> e-ink card)
+-- screenshot.py                  framebuffer grab (portrait/landscape)
+-- scriptlets/ cmds/              device-side scriptlets and command batches used during bring-up
+-- vendor/                        leftover probe-era hotfix bin (unused by this flow, not in git, see vendor/README.md)
+-- studio/                        web workbench: server.py + index.html + tray.py + vendor/ (CodeMirror, Inter fonts)
+-- docs/                          research, design docs and the open-source guides (docs/opensource/)
```

## Verified status (2026-10-16)

Verified on the reference device:

- SpiderCat jailbreak (jb.sh v2.2.1), receipt at `documents/JAILBROKEN.txt`, uid=0
- Scriptlet channel: `documents/*.sh` files appear as books and run as root when opened (SpiderCat bundles sh_integration)
- Render chain: render.py -> ssh pipe -> FBInk GC16 full refresh, fully wireless
- dropbear SSH (key-only, port 2222), KOReader installed via a single-process kpm run
- Dashboard daemon in AC mode: 60 s polling, GL16 partial refresh, GC16 full refresh every 6 rounds, atomic push
- Autostart: real reboot trigger chain verified (2026-10-17): emergency.sh -> autostart.sh restores telnetd/dropbear/iptables and the hooks.d hook brings the dashboard daemon up on its own

Not verified / known broken:

- Battery mode (suspend + RTC wake) failed on the real device, do not use it. See `daemon/DESIGN.md`
- Other models, other firmware: all unverified
- Full list in [INDEX.md](INDEX.md)

## Related docs

| Document | Contents |
|---|---|
| [JAILBREAK.en.md](JAILBREAK.en.md) | Jailbreak: model identification, method matrix, full SpiderCat walkthrough, red lines, pitfall log |
| [SETUP.en.md](SETUP.en.md) | Setup: SSH/telnet channels, KOReader, FBInk, daemon, autostart, each step with verification |
| [INDEX.md](INDEX.md) | Navigation + pending-verification list (which commands were never tested on other models/firmware) |
| [../ideas.md](../ideas.md) | Community project survey (dashboards, KOReader plugins, peripherals, with confidence ratings) |
| [../STUDIO.md](../STUDIO.md) | Web workbench (Studio) design contract and pitfall log |
