# Setup Guide: The Full Post-Jailbreak Toolchain

> **Scope**: this guide was verified on one device: Kindle Oasis 3 (10th gen) + firmware 5.18.2 + SpiderCat (jb.sh v2.2.1), with a Windows 11 PC running Git Bash and Python 3.14. Other models, firmware, or PC platforms: reference only. Prerequisite: the jailbreak from [JAILBREAK.en.md](JAILBREAK.en.md) (you have root and the scriptlet channel).
>
> **Disclaimer**: jailbreaking is at your own risk and unofficially supported. This guide assumes you own an out-of-warranty device. The setup opens a key-only SSH port and an unauthenticated telnet port on the device; both are for your home LAN only, do not replicate this on untrusted networks.

[中文](SETUP.zh.md)

## Contents

1. [Network preparation](#1-network-preparation)
2. [PC toolchain](#2-pc-toolchain)
3. [The first root channel: scriptlets](#3-the-first-root-channel-scriptlets)
4. [KOReader and the SSH channel](#4-koreader-and-the-ssh-channel)
5. [File transfer](#5-file-transfer)
6. [Rendering and pushing](#6-rendering-and-pushing)
7. [The telnet backup channel](#7-the-telnet-backup-channel)
8. [The dashboard daemon](#8-the-dashboard-daemon)
9. [Autostart](#9-autostart)
10. [After a reboot](#10-after-a-reboot)
11. [Troubleshooting quick reference](#11-troubleshooting-quick-reference)
12. [Uninstall and rollback](#12-uninstall-and-rollback)

Conventions: `192.168.1.189` is the example device IP (the default hardcoded in this repo's scripts); substitute your own. Every script honors the `KINDLE_HOST` environment variable — `export KINDLE_HOST=your-device-ip` overrides the default everywhere without touching code. All PC-side commands run in Git Bash.

## 1. Network preparation

### 1.1 Device and PC must be on the wireless side of the same Wi-Fi

- Device: Settings -> Wi-Fi, join your router.
- PC: **join the same Wi-Fi**. Many routers isolate wired ports from wireless clients by default; with the PC on Ethernet, SYNs get dropped while the device side looks perfectly healthy (root-cause analysis in JAILBREAK.en.md pitfall 6.2).
- If your proxy runs in TUN mode, first confirm traffic is not being intercepted by the virtual adapter (`Find-NetRoute -RemoteIPAddress 192.168.1.189`; the outgoing interface must be a physical NIC). Same-subnet traffic is generally left alone (pitfall 6.1).

### 1.2 Find the device IP

- On the device: Settings -> Wi-Fi -> the connected network shows its IP.
- Or scan the ARP table from the PC (Kindle MACs carry Amazon Lab126's `7C-D5-66` prefix):

  ```bash
  ping -n 1 192.168.1.255        # poke the broadcast domain first (-c on some systems)
  arp -a | grep -i 7c-d5-66
  # reference device output looks like: 192.168.1.189   7c-d5-66-xx-xx-xx   dynamic (last three octets masked here)
  ```

Verify connectivity with ARP and ssh, not ping (the device firewall may drop ICMP, and a proxy TUN distorts ping results).

### 1.3 Sleep and USB-mode behavior (learn these once, save hours)

- **USB plugged = drive mode**: `/mnt/us` is unmounted from the device and handed to the host; the device cannot see its own files and Wi-Fi suspends. Unplug to resume. The development rhythm is "plug in to write files -> unplug to execute -> plug in to read logs"; batch as much as possible per unplug cycle.
- **Sleep freezes everything**: when the device sleeps it shuts Wi-Fi off and freezes user processes, so every channel goes silent. Wake with a short power press, or have a scriptlet enable the screensaver hold (the Net Mode script in section 3 keeps it alive for 60 minutes).
- Device facts (measured on the reference unit): screen 1264x1680 / 300 ppi / 8bpp grayscale framebuffer / native portrait at rotate 0 (`eips -i`; `fbink -e` segfaults, do not use); 482 MB RAM (MemTotal 493696 kB); root's home is `/tmp/root`, not `/root`; kernel 4.1.15-lab126; busybox 1.34.1.

## 2. PC toolchain

### 2.1 Python + Pillow

```bash
python --version          # 3.14 on the reference machine; 3.10+ works
python -c "import PIL; print(PIL.__version__)"
# if missing (Pillow lives in the user site-packages here; render.py must NOT run with -I)
python -m pip install --user Pillow
```

### 2.2 Browser

render.py looks for `C:\Program Files\Google\Chrome\Application\chrome.exe` and then `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`; either is enough. For other install locations or non-Windows systems, edit the `CHROME` list at the top of render.py.

### 2.3 SSH key (RSA for dropbear)

```bash
ssh-keygen -t rsa -m PEM -b 2048 -N "" -f ~/.ssh/kindle
```

- `-m PEM` produces the old private-key format. The device's dropbear ships with KOReader (2022+); ed25519 support is unverified on the reference device, so RSA PEM is the tested path.
- The private key `~/.ssh/kindle` never goes into any repository; the public key `~/.ssh/kindle.pub` goes onto the device next.

Confirm Git Bash has ssh:

```bash
ssh -V
```

### 2.4 Fonts (optional, affects card appearance)

- Studio UI: Inter ships with the repo (OFL, `studio/vendor/fonts/`); it works whether or not you install anything.
- Card font stacks: title `"Anthropic Sans", "Inter", sans-serif`; digits/latin JetBrains Mono; CJK Noto Serif SC / Noto Sans SC. All OFL — install them locally to reproduce the screenshots exactly:
  - Inter: https://github.com/rsms/inter/releases
  - JetBrains Mono: https://www.jetbrains.com/lp/mono/
  - Noto Serif SC / Noto Sans SC: https://github.com/notofonts/noto-cjk (or Google Fonts)
  - Skipping JetBrains Mono / Noto still works; the browser falls back to system monospace/serif fonts and only the look differs.
- Anthropic Sans is Anthropic's proprietary typeface (personal-use license). It is **not redistributed** with this repo and lives in no vendor directory. Install it on your own machine and the title picks it up automatically; otherwise cards fall back to Inter.

### 2.5 Studio (web workbench, optional)

```bash
python studio/server.py    # local server only; open http://127.0.0.1:8762
pip install pystray && python studio/tray.py   # or: system-tray resident (icon in the corner)
```

Features: card HTML editing (CodeMirror highlighting), true-render preview (the preview image is render.py's actual output, inside an Oasis device shell with portrait/landscape), one-click push, per-card version history (auto-snapshot on every save), light/dark themes. Annotate mode sends screenshot regions + a request to a local agent that claims and rewrites the card (`POST /api/agent-task` to enqueue, `GET /api/agent-task?claim=1` to claim, `POST /api/agent-result` to write back; contracts in `docs/STUDIO.md`). The server binds 127.0.0.1 only.

## 3. The first root channel: scriptlets

### 3.1 How it works (understand it before you tap)

SpiderCat bundles sh_integration: any `.sh` in `documents/` is indexed as a book and runs as **root** when opened. Four hard constraints:

- **60-second hard timeout**: the process is killed with SIGKILL on timeout. Long jobs must detach with `setsid` and let the scriptlet return instantly.
- **stdout is painted on the screen by default**: script output goes through FBInk (clear screen, then write from line 5). Any script that draws to the screen must put `# DontUseFBInk` in its header, or its own output paints over the image.
- **Working directory is undefined**: start with `cd "$(dirname "$0")"`.
- **Only four header fields exist**: `# Name:`, `# Author:`, `# Icon:`, and `# UseHooks` or `# DontUseFBInk`.

### 3.2 Create a "Net Mode" book

This script does everything in one tap: opens firewall ports 23/2222, starts telnetd, writes authorized_keys, fixes `/tmp/root` permissions, starts dropbear, and holds off the screensaver for 60 minutes. Without KOReader installed the dropbear step fails silently and everything else still works; tap the book again after installing.

Save as `netmode.sh` (**LF line endings required**, see the note below) and replace `PUBKEY` with the contents of your `~/.ssh/kindle.pub` (one line):

```sh
#!/bin/sh
# Name: Net Mode
PUBKEY='ssh-rsa AAAA...paste-your-~/.ssh/kindle.pub-here'
mkdir -p /mnt/us/qoder
printf '%s\n' "$PUBKEY" > /mnt/us/qoder/pubkey.txt
setsid sh -c '
  {
    for P in 23 2222; do
      iptables -C INPUT -p tcp --dport $P -j ACCEPT 2>/dev/null || iptables -I INPUT 1 -p tcp --dport $P -j ACCEPT
    done
    netstat -ltn | grep -q ":23 " || busybox telnetd -l /bin/sh
    chmod 2700 /tmp/root
    mkdir -p /mnt/us/koreader/settings/SSH
    cp /mnt/us/qoder/pubkey.txt /mnt/us/koreader/settings/SSH/authorized_keys
    chmod 600 /mnt/us/koreader/settings/SSH/authorized_keys
    if [ -x /mnt/us/kmc/kpm/packages/koreader/koreader/dropbear ]; then
      ( cd /mnt/us/koreader && /mnt/us/kmc/kpm/packages/koreader/koreader/dropbear -R -s -p 2222 )
    fi
    i=0
    while [ $i -lt 60 ]; do
      lipc-set-prop -i com.lab126.powerd preventScreenSaver 1
      sleep 60; i=$((i+1))
    done
    lipc-set-prop -i com.lab126.powerd preventScreenSaver 0
  } >> /mnt/us/qoder/netmode.log 2>&1
' &
echo NET_MODE_STARTED
```

Why it is written this way:

- The device firewall defaults to `-P INPUT DROP`; inbound 23/2222 must be allowed explicitly. The `-C` check keeps repeated taps from stacking rules.
- `chmod 2700 /tmp/root`: dropbear **silently refuses authentication** when root's home is group-writable (stock 2770). Without this step, SSH always says Permission denied.
- dropbear must start with `/mnt/us/koreader` as its working directory (it resolves paths relative to CWD), and it reads authorized_keys from `/mnt/us/koreader/settings/SSH/` (the KOReader convention), not `/tmp/root/.ssh/`.
- `-R` auto-generates host keys, `-s` disables password logins (key-only), port 2222.
- The screensaver hold only blocks the screensaver, not deep sleep; re-asserting it every 60 seconds keeps the device awake for a while, then it is returned after 60 minutes.

**LF line-ending note**: write the file with `vim`/`nano` or `printf` in Git Bash; if you used a Windows editor, check and fix:

```bash
file netmode.sh           # output must not mention CRLF
# if it does: sed -i 's/\r$//' netmode.sh
```

### 3.3 Deploy and run

1. Connect the Kindle over USB and copy `netmode.sh` into `documents\`.
2. Eject safely. On the Kindle, pull down to refresh the library; **Net Mode** appears as a book.
3. Tap it. Expected: the screen flashes and shows `NET_MODE_STARTED` (the scriptlet paints stdout onto the screen), then returns to the home screen.
4. With the cable unplugged the device now stays awake (the keep-alive loop is running).

### 3.4 Verify telnet works

From the repo root on the PC:

```bash
python -I telnet_run.py "id"
```

Expected output contains:

```
uid=0(root) gid=0(root)
```

Failure triage: `arp -a | grep -i 7c-d5-66` tells you whether the device is on the network at all; if not, it is asleep or Wi-Fi dropped, wake it and retry. If the MAC is there but connections fail, work through JAILBREAK.en.md pitfalls 6.1/6.2 (TUN hijack, router isolation).

## 4. KOReader and the SSH channel

### 4.1 Install KOReader (single process!)

Run over telnet. The device needs internet; the download is about 41 MB and takes a few minutes:

```bash
python -I telnet_run.py "sh /var/local/kmc/sbin/kpm.sh install koreader; echo rc=\$?"
```

While it runs, do **not** tap anything else that could invoke kpm, and do not plug the USB cable. The official equivalent is the search-bar command `;kpm install koreader` (not exercised on the reference device; the scriptlet + kpm.sh route was used instead; both are equivalent).

Verify (values measured on the reference device):

```bash
python -I telnet_run.py "ls /mnt/us/kmc/kpm/packages/koreader/koreader/dropbear && du -sh /mnt/us/kmc/kpm/packages/koreader/"
# expected: /mnt/us/kmc/kpm/packages/koreader/koreader/dropbear
#           about 35.1M
```

History lesson: two concurrent kpm processes writing the same temp kpkg each read a truncated package and the install is corrupted (JAILBREAK.en.md pitfall 6.5). One kpm process at a time, always.

### 4.2 Start dropbear and verify SSH

With KOReader installed, tap **Net Mode** on the device once more (it is idempotent and adds dropbear), or run it manually over telnet:

```bash
python -I telnet_run.py "chmod 2700 /tmp/root; mkdir -p /mnt/us/koreader/settings/SSH; cp /mnt/us/qoder/pubkey.txt /mnt/us/koreader/settings/SSH/authorized_keys; chmod 600 /mnt/us/koreader/settings/SSH/authorized_keys; cd /mnt/us/koreader && /mnt/us/kmc/kpm/packages/koreader/koreader/dropbear -R -s -p 2222 && echo DROPBEAR_OK"
```

Verify from the PC:

```bash
ssh -i ~/.ssh/kindle -p 2222 -o StrictHostKeyChecking=no root@192.168.1.189 id
# expected: uid=0(root) gid=0(root)
```

SSH is now the main channel (key-only, port 2222); telnet is the backup.

SSH failure triage:

| Symptom | Cause | Fix |
|---|---|---|
| Permission denied | authorized_keys in the wrong place (written to `/tmp/root/.ssh/`) | it must be `/mnt/us/koreader/settings/SSH/authorized_keys` |
| Permission denied | `/tmp/root` still stock 2770 (group-writable) | `chmod 2700 /tmp/root` |
| Permission denied | wrong key format | regenerate with `ssh-keygen -t rsa -m PEM` |
| TCP connects then closes | dropbear not running, or wrong CWD | it must be started after `cd /mnt/us/koreader` |
| Connection timeout | device asleep / Wi-Fi down / TUN hijack | see section 1 and the pitfall log |

## 5. File transfer

The device has no sftp-server and scp has no remote side. Everything goes through ssh pipes:

```bash
cat out/card.png | ssh -i ~/.ssh/kindle -p 2222 root@192.168.1.189 "cat > /mnt/us/qoder/card.png"
```

For multiple files, one pipe each; create the target directory first:

```bash
ssh -i ~/.ssh/kindle -p 2222 root@192.168.1.189 "mkdir -p /mnt/us/qoder/autostart/hooks.d"
cat autostart/autostart.sh | ssh -i ~/.ssh/kindle -p 2222 root@192.168.1.189 "cat > /mnt/us/qoder/autostart/autostart.sh"
```

Git Bash trap: **standalone arguments** starting with `/` get rewritten by MSYS into local paths (`/mnt/us/x` becomes `C:/Program Files/Git/mnt/us/x`). Remote command strings inside quotes are unaffected; `push.py` auto-repairs its `--path` argument, and for raw ssh commands keep device paths inside the quoted remote string.

Windows line-ending trap: strip CR before pushing any script to the device (`tr -d '\r' < f.sh | ssh ... "cat > ..."`); CRLF makes ash fail in confusing ways. `autostart/deploy.sh` does this for you.

## 6. Rendering and pushing

### 6.1 The render chain

```
HTML card -> Chrome headless screenshot 1264x1680 -> Pillow 8-bit grayscale
  -> 16-level MEDIANCUT quantize + Floyd-Steinberg dither -> PNG
```

```bash
python render.py cards/push-test-hello.html -o out/test.png
# expected output like: out/test.png  1264x1680  mode=L  bytes=52718
```

Note: render.py must **not** run with `-I` (Pillow lives in the user site-packages and `-I` hides it).

### 6.2 Card HTML constraints

Fixed 1264x1680 size; no flex `gap`, no `position: sticky/fixed`, no animations (both the e-ink screen and the screenshot hate them); font sizes >= 30px; system fonts; white background with black text; avoid fine colored details (everything ends up as 16 gray levels). Working templates in `cards/`.

### 6.3 Pushing (one command)

```bash
python push.py cards/push-test-hello.html            # render -> transfer -> GC16 full refresh (one black flash)
python push.py cards/push-test-hello.html --partial  # GL16 partial refresh, no flash, for small edits
python push.py out/xxx.png                           # push an existing PNG
```

Expected output:

```
已渲染: push-push-test-hello.png
已传输: push-push-test-hello.png -> 192.168.1.189:/mnt/us/qoder/card.png
已刷屏: GC16 全刷
```

(The messages are in Chinese; the card should now be on the screen, which means the whole chain works.) The full agent-facing contract (flags, failure self-checks, hard constraints) is in `push.md` at the repo root.

### 6.4 Manual FBInk refresh (for debugging)

```bash
ssh -i ~/.ssh/kindle -p 2222 root@192.168.1.189 \
  '/mnt/us/libkh/bin/fbink -q -W GC16 -f -g "file=/mnt/us/qoder/card.png"'
```

- Full refresh (clears ghosting): `-W GC16 -f`; partial (no flash): `-W gl16` (without `-f`).
- Waveforms follow the device's own `fbink --help` (FBInk 1.25.0 here supports A2/DU/GL16/GC16/GC16_FAST/GL16_FAST/REAGL/REAGLD/GCK16/GLKW16/GCC16/GLRC16); unsupported modes fall back to AUTO (fallback behavior unverified).
- `fbink -e` segfaults on this device, do not use it; get screen parameters from `eips -i`.

## 7. The telnet backup channel

The fallback when SSH is broken (busybox telnetd, root with no authentication, **home LAN only**):

```bash
python -I telnet_run.py "id"                    # single command
python -I telnet_run.py - < cmds.txt            # batch: one command per line in cmds.txt
TELNET_DEBUG=1 python -I telnet_run.py "uname -a"   # with debug output
```

telnetd dies on reboot; Net Mode / autostart bring it back. Security-wise it is an unauthenticated root door on your LAN; acceptable at home, never on a shared network.

## 8. The dashboard daemon

The daemon runs on the device, periodically painting `/mnt/us/qoder/daemon/current.png` onto the screen; the PC pushes new images at any time and they appear on the next round. Default AC mode (plugged in, always on).

### 8.1 Control from the PC

```bash
python daemon/kd.py start                # deploy scripts to the device + start (idempotent)
python daemon/kd.py status               # process / config / battery / log tail
python daemon/kd.py push out/test.png    # atomic push (tmp+mv), drawn on the next round
python daemon/kd.py push out/test.png --full   # push and request a full refresh next round
python daemon/kd.py log -n 30            # read the log
python daemon/kd.py stop | restart
```

`start` prints `started pid=...`, and `status` then reports `daemon: RUNNING pid=...`. If the device is unreachable, start says `[kd] 设备失联`; go back to section 1.

### 8.2 Refresh discipline

- One round per 60 seconds: GL16 partial refresh; a GC16 `-f` full refresh on the first draw, every 6 rounds, and whenever `meta force_full=1`.
- Pushes are atomic (write `.tmp`, then `mv`), so a half-transferred image is never painted.
- The on-device `config` is re-read every round, so config changes need no restart: `MODE=ac`, `INTERVAL=60`, `FULL_EVERY=6`, `REDRAW_UNCHANGED=1`.
- The `meta` file holds temporary overrides: `force_full=1` (cleared automatically after the full refresh) and `waveform=GC16` (overrides the partial-refresh waveform, whitelist-checked).

### 8.3 Battery mode: tested, failed, do not use

The config offers `MODE=battery` (suspend + RTC wake). **A real-device test on 2026-10-16 failed**: after suspend, neither the RTC alarm (rtc0 wakealarm accepted the write) nor the power button woke the device; only a long-press forced reboot recovered it. The kindle-dash mxc_rtc nodes do not exist on this hardware (that project targets older models). Details and the untested alternatives are in `daemon/DESIGN.md`. Use `MODE=ac` for plugged-in setups.

### 8.4 Verified checklist (measured on the reference device)

- AC mode resident: preventScreenSaver=1, GL16 partial refresh, GC16 full refresh every 6 rounds, full first draw
- Atomic push drawn on the next round; `--full` sets meta and it is consumed
- stop/start/status/log/push all work; repeated start is idempotent; flock rejects a second instance

## 9. Autostart

### 9.1 Mechanism (full research in `autostart/DESIGN.md`)

The SpiderCat jailbreak leaves an upstart job on the rootfs, `/etc/upstart/kmc.conf` (`start on framework_ready`); its pre-start checks for `/mnt/us/emergency.sh` and, if present, chmod +x and runs it as root. The `org.kindlemodding.emergency_launcher` entry in appreg.db is a redundant trigger. This is the author's rescue hook and the only boot hook outside the rootfs available to users; it requires zero rootfs writes. The pre-start blocks until the script exits, so the hook must return in seconds and be idempotent.

This project's chain:

```
/etc/upstart/kmc.conf (framework_ready)
  -> /mnt/us/emergency.sh            3-line bootstrap
  -> /mnt/us/qoder/autostart/autostart.sh   all logic (idempotent)
       iptables allow 23/2222 (deduped with -C)
       telnetd 0.0.0.0:23 (start only if not already listening)
       chmod 2700 /tmp/root
       dropbear -R -s -p 2222 (CWD=/mnt/us/koreader)
       hooks.d/*.sh each started detached with setsid (output into hooks.log)
```

### 9.2 Deploy

```bash
cd autostart
./deploy.sh            # deploy emergency.sh + autostart.sh to the device, syntax-check
./deploy.sh --check    # syntax check only (SYNTAX_OK)
./deploy.sh --smoke    # run autostart.sh once by hand and print the log (idempotent, safe to repeat)
./deploy.sh --status   # listeners + iptables rules + /tmp/root perms + log tail
```

The deploy script strips CR for Windows-authored files automatically.

### 9.3 Verify the state

```bash
./deploy.sh --status
# expected:
#   netstat: one LISTEN each for 0.0.0.0:23 and 0.0.0.0:2222
#   iptables: exactly one ACCEPT each for dpt:23 and dpt:2222 (no stacking across runs)
#   /tmp/root perms 2700
#   autostart.log tail shows === autostart invoked / done
```

**Pending**: the real reboot trigger chain has not been verified yet (the hop where framework_ready runs emergency.sh). The reboot verification plan (pass criteria, triage order, fallbacks) is written in `autostart/DESIGN.md` sections 4 and 5; follow it when a reboot window is available.

### 9.4 Hooking in your own boot tasks

Drop an executable `.sh` into `/mnt/us/qoder/autostart/hooks.d/` on the device; autostart.sh starts it detached (root, setsid) on every boot, with stdout/stderr into `hooks.log`. The script must daemonize itself or return to background quickly. A dashboard-daemon hook (`dashboard.sh`) is a reserved, not-yet-implemented slot (see INDEX.md).

## 10. After a reboot

A reboot clears all runtime state: telnetd, dropbear, iptables rules, `chmod 2700 /tmp/root`, the daemon. Everything on persistent partitions survives: all scripts and logs under `/mnt/us`, the fbink binary, authorized_keys, KOReader, and the jailbreak itself.

Recovery, in order of preference:

1. **Once autostart is verified**: do nothing; everything comes back on boot.
2. **Tap Net Mode (or Run 08) on the device**: restores telnet + SSH + firewall + the 60-minute keep-alive in one second. Then run `python daemon/kd.py start` from the PC to bring the daemon up.
3. **Device at hand, no PC**: tap the `q09-daemon` scriptlet on the device (`documents/q09-daemon.sh`, which calls `/mnt/us/qoder/daemon/start.sh` directly; whether it has been indexed as a book is unverified).

Reboot commands (checked): prefer `/sbin/reboot`; fallback `lipc-set-prop com.lab126.powerd deviceRestart 1` (property verified present). Note that the commonly cited `lipc-set-prop com.lab126.cmd reboot do` does **not** work on this device (`lipc-probe com.lab126.cmd` has no reboot property).

## 11. Troubleshooting quick reference

| Symptom | Check first | Verdict and action |
|---|---|---|
| SSH and telnet both dead | `arp -a \| grep -i 7c-d5-66` | MAC present = device alive, check routing/firewall; MAC absent = asleep or Wi-Fi down, wake it or tap Net Mode |
| ping works, ports do not | `Find-NetRoute -RemoteIPAddress <ip>` | outgoing interface TUN (Meta) = proxy hijack; add a host route or route-exclude-address |
| Device side healthy, PC cannot connect | is the PC on Ethernet? | wired/wireless isolation; put the PC on the same Wi-Fi |
| SSH Permission denied | table in 4.2 | authorized_keys path / chmod 2700 / key format |
| Transfer dies mid-write | did the cable come out during a write to `/mnt/us`? | unplugging unmounts `/mnt/us`; long jobs must run with the cable out |
| Scriptlet tap does nothing | does the script return instantly? | 60-second timeout kills it; detach with `setsid`; add `# DontUseFBInk` to drawing scripts |
| Refresh shows nothing | fbink path and flags | path is `/mnt/us/libkh/bin/fbink`; `-g "file=path"`; never `-e` (segfault) |
| kpm install corrupted | did two run at once? | rerun `kpm.sh install koreader` as a single process |
| Ghosting on screen | how long since the last full refresh? | manual `fbink -q -W GC16 -f -g "file=..."`, or `kd.py push --full` |
| Daemon not starting | `python daemon/kd.py status` | read start output and `daemon.log`; flock is single-instance, the second instance exits |

## 12. Uninstall and rollback

- **Reset runtime state only** (keep the jailbreak): reboot once; telnetd/dropbear/iptables/daemon are all gone. To disable autostart, delete `/mnt/us/emergency.sh` on the device.
- **Remove project files**: the whole `/mnt/us/qoder/` tree and this project's `*.sh` files in `/mnt/us/documents/`. To uninstall KOReader, use kpm's uninstall path (KPM packages carry an uninstall hook; check `kpm.sh` help for the exact subcommand).
- **Full rollback (remove the jailbreak)**: factory reset, see JAILBREAK.en.md section 5.4 (an empty `DO_FACTORY_RESTORE` file in the USB root, then restart).
