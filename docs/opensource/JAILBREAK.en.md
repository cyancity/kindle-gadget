# Jailbreak Guide: Kindle Oasis 3 + SpiderCat

> **Scope**: this guide was verified on one device: Kindle Oasis 3 (10th gen, 2019, CN 8GB Wi-Fi) + firmware 5.18.2 + SpiderCat (jb.sh v2.2.1). Other models or firmware versions: reference only. Method availability, coverage ranges and command output may all differ. Before touching anything, re-check your own combination against the official wizard at kindlemodding.org.
>
> **Disclaimer**: jailbreaking is an unofficial modification, at your own risk: you can brick the device, lose warranty, and (rarely, per community reports) get your Amazon account flagged. This guide assumes you own the device, it is out of warranty, and its content can be wiped.

Next step after jailbreaking: [SETUP.en.md](SETUP.en.md) covers the SSH channel and the rest of the toolchain.

[中文](JAILBREAK.zh.md)

## Contents

1. [Before you start: identify model and firmware](#1-before-you-start-identify-model-and-firmware)
2. [Choosing a jailbreak](#2-choosing-a-jailbreak)
3. [Preparation](#3-preparation)
4. [Full SpiderCat walkthrough](#4-full-spidercat-walkthrough)
5. [Red lines](#5-red-lines)
6. [Pitfall log](#6-pitfall-log)

## 1. Before you start: identify model and firmware

Jailbreak availability is a hard gate on model and firmware. Get two ground truths first.

### 1.1 The screen truth (most reliable)

On the Kindle: Settings -> Device Options -> Device Info. Write down the **model** and **firmware version**. On the reference device: Oasis (10th Generation) / 5.18.2.

### 1.2 The USB truth (cross-check)

Connect the Kindle over USB (it mounts as a USB drive), then in PowerShell:

```powershell
Get-Content H:\system\version.txt
# reference device output: Kindle 5.18.2 (443455 025)
```

Two traps:

- **release_notes lies**. `H:\system\release_notes\` may contain only a stale release-notes file (on the reference device: a 5.16.5 note from 2023-11). It records one historical update, not the current firmware. Trust `version.txt` and the screen instead.
- **Windows Explorer hides the `system` folder**. If Explorer does not show it, use PowerShell or `ls` in Git Bash. In USB drive mode the `system` folder is readable and writable.

### 1.3 Serial number and model

Characters 4 to 6 of the serial number are the devcode; kindlemodding's models.json maps it to a model. The reference device serial is G000WL****** (masked here), devcode `0WL`, which maps to `KindleOasis3WiFi8GB`, platform Zelda / board Stinger, released 2019, shipped with 5.12.0, and **the model's last firmware (last_firmware) is 5.18.2**; the product line is frozen.

Screen resolution is another hint: Oasis 3 is 1264x1680 (Paperwhite 5 is 1236x1648, Scribe is 1860x2480).

### 1.4 Firmware window pressure

Because 5.18.2 is already the end of the line for this model, there is no "update once and the window closes forever" pressure here. Even if Amazon ships a minor bump, SpiderCat (covers up to 5.19.5) and Nosebleed (up to 5.18.6) still apply. Older devices stuck on 5.16.x are a different story: an update can permanently close every jailbreak window, so those need OTA blocking first (see section 3).

## 2. Choosing a jailbreak

Read the official Jailbreak Wizard at kindlemodding.org first; it lists the methods that apply to your model and firmware. The table below is the computed result for KOA3 + 5.18.2 (from the official jailbreaks.json, October 2026):

| Method | KOA3 firmware range | Works on 5.18.2 | Prerequisites | Injection |
|---|---|---|---|---|
| **SpiderCat** | 5.16.3 – 5.19.5 | yes | none (no registration, no ads) | sideload one azw3 into documents, open it from the library |
| Nosebleed | 5.16.4 – 5.18.6 | yes | none | two files to the USB root, open kindlemodding.org/nosb in the experimental browser |
| AdBreak | 5.18.1 – 5.18.5.0.1 | yes | ad-enabled (Special Offers) and registered | replace the ad `details.html` under `system/.assets/`, then tap the ad |
| WinterBreak2 | 5.6.1.1 – 5.16.3 (whitelist includes 5.16.5) | no | none | open penguins184.xyz/wb2 in the browser |
| WinterBreak | 5.18.0.2 and lower | no | registration + Kindle Store access | Mesquito-based, dead since 5.18.1; the CN store closed in 2023 |

Selection logic:

- **On 5.18.x, SpiderCat is the first choice**: fewest prerequisites (no ads, no registration, no store), widest coverage (to 5.19.5), least physical interaction (open one book). This is what the reference device used.
- Ad-enabled devices can keep AdBreak as a fallback. Conversely, if you go with SpiderCat, **do not pay USD 19.99 to remove Special Offers**: the ad-free "fake book cover as lock screen" route is mutually exclusive with AdBreak. Keeping ads is harmless.
- Older methods (LanguageBreak, diunes, USBarm, KUAL+MRPI) top out at 5.16.2.1.1 and none work on 5.18.2. Older Chinese tutorials describing KUAL/MRPI flows should not be followed.
- All of these jailbreaks live in the userstore (patchedUks.sqsh) and never touch the rootfs. Failures can be rolled back with a factory reset (section 5); it is reversible and brick risk is low.

## 3. Preparation

1. **Confirm your firmware is inside a window** (section 1) and the method's prerequisites (SpiderCat has none).
2. **Do not fight updates manually** (only applies to models whose last_firmware is already installed): never put any `update*.bin` in the USB root, never tap "Update Your Kindle" in settings. For older devices that need OTA blocking (fill the disk to 50-90 MB free, etc.), see the FAQ on kindlemodding.org.
3. **Prepare a fallback**: download the Nosebleed package to your PC now, so you are not hunting for it if SpiderCat fails.
4. **Hash tools**: Git Bash has `sha256sum`, or use PowerShell `Get-FileHash`.
5. **Expectations**: the whole procedure is file operations plus one book tap. Wi-Fi must stay on until it finishes. The usual failure mode is simply "nothing happened"; run it again.

## 4. Full SpiderCat walkthrough

Recorded flow from the reference device (Windows + Git Bash, USB drive mounted at `H:`, adjust to your own drive letter).

### 4.1 Download and verify spidercat.azw3

Download `spidercat.azw3` from the SpiderCat page reachable through kindlemodding.org, then verify:

```bash
sha256sum spidercat.azw3
# file fetched 2026-10 on the reference device:
# F07E25C2003CAC4BFB381D70AB784C8B0CF996CD6A499A18116405B224046062  spidercat.azw3
# 484289 bytes
```

Upstream publishes no separate checksum. The hash above corresponds to the file distributed during the jb.sh v2.2.1 era; if upstream has updated since, trust the official page. Verifying "the source is kindlemodding.org over HTTPS" is the practical baseline. This azw3 executes code as root on your device; do not accept copies from random mirrors.

### 4.2 Sideload onto the device

1. Connect the Kindle over USB and wait for it to mount as a USB drive.
2. Copy `spidercat.azw3` into `documents\`.
3. Verify the on-device hash matches the local one (protects against a corrupted copy):

   ```bash
   sha256sum H:/documents/spidercat.azw3
   ```

4. Eject the drive safely.

### 4.3 Open the book (the only hands-on step)

1. Turn Wi-Fi on and **keep the device online until the flow finishes**.
2. From the home screen, open the library, find the book named **SpiderCat**, open it.
3. Expected behavior (official description, matched on the reference device):
   - a few seconds of blank page or cover only, **keep waiting**;
   - text scrolls from the top of the screen to the bottom, ending with **Bang!** as the script starts;
   - an **application error** popup may appear; that is expected, ignore it.
4. If the book is missing: pull down to refresh the library, or restart the device and look again.

### 4.4 Confirm the jailbreak

Reconnect USB and check three markers (all matched on the reference device):

```bash
cat H:/documents/JAILBROKEN.txt
# You are jailbroken! (jb.sh v2.2.1)

cat H:/privesc_marker.txt
# jb.so constructor: uid=0 euid=0 pid=15544     <- root code really ran

ls -la H:/libkh/bin/fbink
# about 1.38 MB; FBInk 1.25.0 dropped in by jb.sh
```

`system/version.txt` should still read 5.18.2; the firmware was untouched.

### 4.5 Reboot and install the package-manager pieces

The official flow requires one reboot right after jailbreaking. After the reboot (Wi-Fi still on):

1. In the home search bar type `;kpm update` and press enter. Expected: a few lines scroll at the top of the screen, then back to the home screen.
2. In the search bar type `;kpm install koreader` and press enter. Expected behavior is the same; a KOReader icon appears in the library when done.

Note from the reference device: those two search-bar commands were never run by hand; KOReader was installed later through the scriptlet channel with `sh /var/local/kmc/sbin/kpm.sh install koreader` as a single process (see SETUP.en.md section 4). Both paths are equivalent; the search bar is the official standard route. **Either way, only one kpm process may run at a time**: concurrent installs corrupt the package (pitfall 6.5).

### 4.6 What you have now

- Root execution: SpiderCat bundles sh_integration, so any `.sh` in `documents/` is indexed as a book and runs as root when opened (60-second timeout; see SETUP.en.md section 3 for the mechanics).
- `/mnt/us/libkh/bin/fbink`: FBInk 1.25.0, full build (images + TrueType).
- `/var/local/kmc/sbin/kpm.sh`: the KPM package manager (not on PATH).
- Stock tooling: busybox 1.34.1 (includes telnetd), eips, lua, iptables, curl. No dropbear/sshd/python/perl.

Everything that follows lives in [SETUP.en.md](SETUP.en.md).

## 5. Red lines

### 5.1 Never write to the rootfs

10th-generation and later Kindles have secure boot. A damaged rootfs has **no local recovery path** (official partition backup/restore only works on 8th gen and earlier), and KPM explicitly forbids it. Everything in this project lives under `/mnt/us` (userstore, executable bits honored) and `/var/local` (writable, not rootfs, survives reboots).

### 5.2 Keep OTA updates blocked

- After jailbreaking, jb.sh's system patches block OTA (per upstream documentation; the blocking behavior itself was not separately verified on the reference device, whose last_firmware was already installed, so there was little pressure to begin with).
- Follow three rules yourself: never tap "Update Your Kindle" in settings; never leave `update*.bin` or `update.bin.tmp.partial` in the USB root; never install `.bin` files from untrusted sources.
- Manual firmware updates (deliberate, and only after confirming the new firmware still has a jailbreak) go through an Amazon-signed `.bin` in the USB root.

### 5.3 Suspend experiments require a human present

A bare `echo mem > /sys/power/state` on this 5.18.2 device is a one-way ticket: neither the RTC alarm nor the power button wakes it, only a long-press forced reboot does. Tested and recorded in `daemon/DESIGN.md`. Any suspend/sleep experiment requires the user in the room before you run it.

### 5.4 Factory reset (the last resort)

- **Trigger**: place an empty file named `DO_FACTORY_RESTORE` in the USB root and restart the device (per KindleModding documentation). A factory reset removes the jailbreak and all content.
- **Forced reboot** (the only remedy for a hang): hold the power button for 20+ seconds. The jailbreak lives in the userstore and survives reboots; you only lose runtime state (telnetd, iptables rules, etc.).
- After a factory reset, redo section 4 to jailbreak again.

## 6. Pitfall log

These are the routes that genuinely dead-ended during this project's early exploration, written down so readers can skip them. All of them happened after the jailbreak, while bringing up the SSH channel.

### 6.1 PC-side proxy TUN hijacks the route (symptom: connects, then instantly resets)

Symptom: `telnet 192.168.0.100 23` established TCP but the peer sent no data and reset; the SSH port showed the same.

Root cause: the Clash TUN virtual adapter on the PC (interface named Meta, 198.18.0.1/30) intercepted traffic headed for the Kindle; the tunnel interface answered the TCP handshake and the Kindle was never contacted. How to check:

```powershell
Find-NetRoute -RemoteIPAddress 192.168.1.189
# look at the outgoing interface: "Meta"/TUN means hijacked; a physical NIC is what you want
```

Fixes (either):

```powershell
# one-off host route (needs admin, affects only this IP)
route add 192.168.1.189 mask 255.255.255.255 192.168.1.1
route delete 192.168.1.189   # undo
```

Or, in a Clash Verge override config, exclude LAN ranges from TUN (reload the core after saving or it does nothing):

```yaml
tun:
  enable: true
  route-exclude-address:
    - 192.168.1.0/24
    - 10.0.0.0/8
    - 172.16.0.0/12
```

Follow-up finding: when the PC and the Kindle are on the **same subnet**, Clash TUN leaves same-subnet traffic alone. It intercepted here because the PC was on a wired subnet and the Kindle on a different wireless one. Putting both devices on the same subnet fixes most proxy setups without touching them.

### 6.2 Router isolation between wired and wireless (symptom: device is healthy, nobody answers)

Symptom: everything on the device side looked right: telnetd listening on `0.0.0.0:23`, iptables rules inserted at the top of INPUT, the device could ping its gateway, and the PC could resolve its MAC through ARP. But SYNs from the PC vanished and port scans came back empty.

Root cause: the router isolates **wired ports from wireless clients** (AP isolation / client isolation). The device's default firewall policy is `-P INPUT DROP`, and packets crossing the isolation boundary never reach it. The isolation exists only between wired and wireless; the wireless side alone has none.

Fix: put the PC on the same Wi-Fi (the wireless side) and the isolation disappears. Verified 2026-10-16: with the PC on Wi-Fi, SSH connected directly. If you would rather not touch router settings, this is the cheapest route.

Suggested triage order: `arp -a` first (MAC present = layer 2 is fine), then device-side logs for listening state and firewall, and only then suspect router isolation.

### 6.3 USB networking (RNDIS) does not work on Windows 11

Symptom: after `lipc-set-prop -i com.lab126.volumd useUsbForNetwork 1` plus hal `usbUnconfigured`/`usbPlugOut` on the device, `usb0` came up fine and the screen showed USB NETWORK MODE; but Windows showed neither a drive nor a new network adapter, only a COM5 serial port that failed to open.

Root cause (local forensics plus kernel-source cross-check): the device switched into the kernel's legacy `g_ether` gadget, RNDIS product ID VID_0525:PID_A4A2. Its RNDIS control interface (Class 02/SubClass 02) matches Windows' `usbser.inf`, which grabs it as a serial port; the in-box `rndiscmp.inf` only binds devices that send MS OS 1.0 descriptors, which legacy gadgets never do, so **no network adapter ever appears**. COM5 is not a console either (the device has no ACM function), so Code 10 is inevitable. The same symptom is documented since 2016; the old fix was a self-signed custom driver, not worth repeating on Windows 11.

Fix evaluated and rejected: getting a NIC on Windows requires building an RNDIS function through configfs on the device with forged MS OS descriptors, after unbinding Amazon's own mtpgadget, and it is unknown whether the KOA3 kernel even ships `libcomposite`/`usb_f_rndis`. Not worth the risk.

Side facts: `useUsbForNetwork` is a volatile volumd property and resets on reboot; Oasis 2/3 have prior kernel-panic reports around `usbUnconfigured`. The reference device survived, but the host-side enumeration stayed half-dead until the cable was replugged.

Conclusion: on this model, plugging USB locks it into drive mode (`/mnt/us` unmounts from the device and Wi-Fi suspends), so USB-tethered development is a non-starter anyway. Use Wi-Fi.

### 6.4 Sleep freezes everything

Symptom: after tapping a book and unplugging, within about a minute the PC still saw the device in ARP but no port answered anything.

Root cause: Kindle sleep freezes user processes and shuts Wi-Fi off. `preventScreenSaver` only blocks the screensaver, not deep sleep; a file-polling resident agent simply stops running while the device sleeps. Tapping a book guarantees the device is awake, which is why book-tap triggers beat background polling.

Fix: during development, a scriptlet sets `lipc-set-prop -i com.lab126.powerd preventScreenSaver 1` (it only blocks the screensaver; re-asserting it periodically keeps the device awake for a while). The real solution is the dashboard daemon's AC mode running resident with its own sleep policy (SETUP.en.md section 8).

### 6.5 Concurrent kpm installs corrupt the package

Symptom: the KOReader download stalled at 10% and the install failed.

Root cause: two install flows ran concurrently; two kpm processes wrote the same temp file `/mnt/us/kmc/kpm/packages/tmp/koreader_*.kpkg` and both read a truncated package.

Fix and discipline: only one kpm at a time; long jobs must detach with `setsid` (scriptlets have a hard 60-second timeout) and the cable must stay out during writes (unplugging unmounts `/mnt/us` and kills anything writing there). Two rules cover it: batch commands per unplug cycle, and never run two installs that write the same file.

### 6.6 Trust the device's own help output, not memory

Half the FBInk flags written from memory early on were wrong (`-r/--rot`, `-l/--light`, `-w A_DUST`, `-P --No-pep`, `--discard` do not exist; the real meanings are `-r`=rpadded, `-w`=wait, `-P`=progressbar). Always check `fbink --help` on the device and the source. Also, `fbink -e` segfaults on this device, do not use it; get screen parameters from `eips -i` instead.
