# 文档导航与验证状态

[English](#english)

kindle-gadget 的开源文档。中文版为主，英文版内容对齐：

| 文档 | 内容 | English |
|---|---|---|
| [README.zh.md](README.zh.md) | 项目是什么、架构、快速开始、仓库结构 | [README.en.md](README.en.md) |
| [JAILBREAK.zh.md](JAILBREAK.zh.md) | 越狱：机型/固件判定、方案选型表、SpiderCat 全步骤、红线、踩坑实录 | [JAILBREAK.en.md](JAILBREAK.en.md) |
| [SETUP.zh.md](SETUP.zh.md) | 越狱后配置：SSH/telnet 通道、KOReader、渲染链、daemon、autostart，每步含验证 | [SETUP.en.md](SETUP.en.md) |

仓库内更深的参考资料（英文/中文混合，面向维护者）：

| 文件 | 内容 |
|---|---|
| `AGENTS.md`（仓库根） | 设备事实与全部踩坑的权威来源，内容与设备实测一致 |
| `push.md` | push.py 的 agent 调用契约 |
| `daemon/DESIGN.md` | daemon 设计、刷新纪律、battery 模式失败考证 |
| `autostart/DESIGN.md` | 开机自启机制考证、重启验证方案、排查预案 |
| `docs/ideas.md` | 社区玩法调研（含可信度分级） |
| `docs/STUDIO.md` | 网页工作台（Studio）的设计契约与踩坑实录 |

## 验证基线

**本教程实测机型：Kindle Oasis 3（第 10 代，8GB Wi-Fi）+ 固件 5.18.2 + SpiderCat（jb.sh v2.2.1），PC 侧 Windows 11 + Git Bash。** 下文把「在这台机器上真机跑过」的记为已验证，其余全部列明。

## 已验证清单（真机，2026-10-16/17）

- 越狱：SpiderCat 全流程（4.1–4.6），回执 `documents/JAILBROKEN.txt`，privesc marker uid=0
- scriptlet 通道：`documents/*.sh` 点书以 root 执行；60 秒超时、stdout 刷屏、DontUseFBInk 均实测确认
- 渲染链：render.py（Chrome headless + Pillow 16 阶抖动）→ ssh 管道 → `fbink -W GC16 -f` 全刷，无线闭环
- SSH：dropbear（KOReader 二进制）端口 2222 仅密钥；authorized_keys 路径、`chmod 2700 /tmp/root`、CWD 坑均实测确认
- telnet：busybox telnetd 0.0.0.0:23 + `telnet_run.py`
- daemon：ac 模式常驻（60s 轮询、GL16 局刷、每 6 轮 GC16 全刷）、原子推送、flock 单实例、stop/start/status/log/push 全链路
- autostart：**真实触发链已验证**（2026-10-17 00:43 真机重启）：`emergency.sh` → `autostart.sh` 自动恢复 telnetd/dropbear/iptables，`hooks.d` 自动拉起 dashboard daemon（横屏 fb 旋转校准正确）；`deploy.sh --check/--smoke` 也已通过
- 设备事实：1264x1680/300ppi/8bpp/rotate 0（`eips -i`）、RAM 482MB、root home `/tmp/root`、`fbink -e` 段错误、busybox 1.34.1、无 python/perl

## 未完成清单（明说，别踩）

### 未在真机上完成验证（等待后续工作）

1. **`kpm launch koreader`**：KOReader 的 KPM 启动方式未试过。
2. **`q09-daemon` scriptlet**：`documents/q09-daemon.sh` 是否已被索引成书未验证（内容本身简单：调 daemon/start.sh）。
3. **`;kpm update` / `;kpm install koreader` 搜索框路径**：本机未由人执行过（KOReader 经 scriptlet + kpm.sh 单进程安装成功）。两条路径按官方文档等价。
4. **daemon 日志轮转的实际效果**：>200KB 裁剪逻辑在，未自然触发过阈值。
5. **meta waveform 非 GL16/GC16 的显示效果**、**fbink 对不支持波形的 AUTO 降级行为**：代码路径在，未真机验。
6. **其他 battery 替代方向**（rtc2 闹钟、busybox rtcwake、powerd 原生休眠）：battery 模式实测失败后未再尝试，方向按可信度排序记录在 `daemon/DESIGN.md`。

### 未在其他机型/固件/环境上验证过

7. **一切命令**。全部只在 KOA3 + 5.18.2 + SpiderCat jb.sh v2.2.1 上跑过。换机型（Paperwhite/Scribe/10 代前后）或换固件，路径（`/mnt/us/kmc/...`、`/tmp/root`）、机制（kmc.conf、scriptlet）、甚至越狱方案本身都可能不同，必须按 JAILBREAK.zh.md 第 1–2 节重新判定。
8. **JAILBREAK.zh.md 第 2 节选型表中其他方案**（WinterBreak2 / Nosebleed / AdBreak / WinterBreak）：只做过资料实算与表格整理，未实测任何一条。固件区间数字来自官方 jailbreaks.json（2026-10），以官方向导为准。
9. **PC 侧非 Windows 环境**：render.py 的浏览器路径是硬编码的 Windows Chrome/Edge；`--path` 的 MSYS 改写修复只针对 Git Bash；macOS/Linux 主机需要自己改。Python 版本只测过 3.14。
10. **dropbear ed25519 密钥**：未测，用的是 RSA PEM。
11. **`.sh` 之外的 scriptlet 扩展**、`# UseHooks` 用法、`# Icon:` 字段：机制来自上游源码核对，本机只用过默认路径。

### 实测失败（有记录，勿踩）

12. **daemon battery 模式**（suspend + RTC 唤醒）：真机失联，长按重启才恢复。`daemon/DESIGN.md` 有全程记录。
13. **`fbink -e`**：段错误，禁用。
14. **`lipc-set-prop com.lab126.cmd reboot do`**：本机无此属性，重启用 `/sbin/reboot`。
15. **USB 切网卡（RNDIS）+ Windows 11**：走不通，根因与放弃理由见 JAILBREAK.zh.md 踩坑实录 6.3。

## English

Open-source documentation for kindle-gadget. The Chinese files are primary; the English files mirror them:

| Doc | Contents |
|---|---|
| [README.en.md](README.en.md) | what it is, architecture, quick start, repo layout |
| [JAILBREAK.en.md](JAILBREAK.en.md) | jailbreak: model/firmware ID, method matrix, SpiderCat walkthrough, red lines, pitfall log |
| [SETUP.en.md](SETUP.en.md) | post-jailbreak setup: SSH/telnet, KOReader, render chain, daemon, autostart, each step verified |

Verification baseline: everything above was verified on exactly one device (Kindle Oasis 3, firmware 5.18.2, SpiderCat jb.sh v2.2.1, Windows PC). The autostart reboot trigger chain and the daemon boot hook were verified by a real reboot (2026-10-17); battery-mode alternatives, all other jailbreak methods, and all non-Windows hosts remain unverified; battery mode and `fbink -e` are known broken on this device.
