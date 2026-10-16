# kindle-gadget 看板 daemon 设计

目标：常驻把 `/mnt/us/qoder/daemon/current.png` 周期刷上屏，PC 侧随时推新图，下一轮刷出；插电常驻（ac）与电池休眠（battery）两种电源模式可配置。设备：Kindle Oasis 3，固件 5.18.2，内核 4.1.15-lab126，busybox 1.34.1（ash），无 python/perl。

## 布局

repo 侧（本目录）：

| 文件 | 用途 |
|---|---|
| `kd.py` | PC 侧控制：start / stop / status / restart / log / push |
| `device/dashboard.sh` | daemon 本体（busybox ash，部署到设备） |
| `device/start.sh` `device/stop.sh` | 设备侧启停（kd.py 调用，设备 shell 也可直接跑） |
| `device/config` | 默认配置（首次部署落盘，之后设备上的为生效版本） |
| `research/kindle-dash/` | 电源机制考证用的 pascalw/kindle-dash 源码存档 |

设备侧（`/mnt/us/qoder/daemon/`，rootfs 零写入）：

```
dashboard.sh  start.sh  stop.sh  config      # 脚本与配置
current.png                                  # 看板内容（PC 推送）
meta                                         # 可选，刷新策略覆盖（KEY=VALUE）
draw.png                                     # daemon 每轮的绘制副本（避免读到推到一半的图）
daemon.log                                   # 日志（>200KB 时裁到 100KB）
daemon.pid  .lock                            # pid 定位 + flock 单实例锁
```

## 内容契约

- daemon 只认 `current.png` 一个文件，每轮 `cp` 成 `draw.png` 后交给 fbink，保证 PC 推送推到一半时不会把半张图刷上屏。
- 推送必须原子：先写 `current.png.tmp` 再 `mv`（kd.py 的 push 已封装）。手动 `cat > current.png` 也能工作，最坏情况某一轮刷出半张图，下一轮自愈。
- `meta`（可选）支持：
  - `force_full=1`：下一轮强制全刷，刷完 daemon 自动清回 0。
  - `waveform=<MODE>`：覆盖局部刷波形（白名单校验，不合法忽略）。
  - meta 每轮重读，PC 改完无需重启。全刷固定用 GC16，`waveform` 只作用于局部刷。

## 刷新纪律

- 局部刷（默认）：`fbink -q -W GL16 -g "file=draw.png"`。
- 全刷：`fbink -q -W GC16 -f -g "file=draw.png"`。
- 触发全刷的条件（任一）：daemon 启动后首刷；`meta force_full=1`；每 `FULL_EVERY` 轮插一次（`config` 可配，0=从不自动全刷）。
- `REDRAW_UNCHANGED=1`（默认）时内容没变也照刷，靠周期全刷自愈残影；设 0 则只在新图或全刷到期时刷。
- 波形以设备 fbink 1.25.0 `fbink -h` 为准：Oasis 3 支持 A2/DU/GL16/GC16 等，不支持的模式会降级 AUTO。

## 电源机制考证

### kindle-dash（pascalw）的做法（读 src/dash.sh `rtc_sleep()`）

```sh
RTC=/sys/devices/platform/mxc_rtc.0/wakeup_enable
echo -n "$duration" >"$RTC"        # 写"多少秒后唤醒"
echo "mem" >/sys/power/state       # suspend-to-RAM，RTC 到点拉起
```

配套：`lipc-set-prop com.lab126.powerd preventScreenSaver 1` 防休眠、`eips -g`（局部）/`eips -f -g`（全刷）。它调度用 cron 表达式 + 自带 Rust 程序算下次唤醒秒数，并用 `/etc/init.d/framework stop` 关掉 UI 省电。

### 本机核对结果（2026-10-16 实测）

| 项 | 结果 |
|---|---|
| `/sys/devices/platform/mxc_rtc.0/wakeup_enable` | **不存在**。Oasis 3 不用 mxc_rtc，kindle-dash 的节点路径不能照搬 |
| RTC 设备 | rtc0/rtc1 = max77796 PMIC RTC，rtc2 = i.MX SNVS RTC（读 `/sys/class/rtc/rtc*/device` 确认） |
| `/sys/class/rtc/rtc0/wakealarm` | **可写**：写 epoch 秒成功，回读一致，`echo 0` 取消成功（已实测，未挂起） |
| `/sys/power/state` | `freeze standby mem`，支持 suspend-to-RAM |
| busybox `rtcwake` | 存在（`rtcwake -d /dev/rtc0 -m mem -s N` 是 wakealarm+mem 的等价封装） |
| `lipc` / powerd | `preventScreenSaver` 当前值 1，可读写；`isCharging` 可读 |

### 模式 ac（插电常驻，已跑通）

- 启动时 `lipc-set-prop -i com.lab126.powerd preventScreenSaver 1`，每轮循环不重复设（一次即生效，stop 时回 0）。
- 主循环：刷屏 → sleep `INTERVAL` 秒（5 秒分片，保证 TERM 能及时打断）→ 下一轮。
- 代价：设备整体不睡，插电无感；电池供电时掉电较快（每轮日志记录电量，<20% 且未插电时告警）。

### 模式 battery（休眠 + RTC 唤醒）——实测失败，勿在无人值守时开启

代码路径保留、config 可切，但 **2026-10-16 真机实测：设备失联，靠强制重启恢复**。

实测记录：MODE=battery 启动后首刷正常，随后 `echo mem > /sys/power/state` 挂起（布闹钟写入 rtc0/wakealarm rc=0）。日志中 90 分钟周期内 **零条唤醒记录**；电源键短按无法唤醒；最终用户长按电源强制重启恢复。重启后 /mnt/us 上的脚本、日志全部还在（持久分区），`kd.py start` 一键重建。

失败原因分析（推断）：
- 写 `/sys/class/rtc/rtc0/wakealarm` 成功不等于闹钟电源域在 suspend 时有效。max77796 的 alarm 硬件可能需要额外寄存器/中断路由配置（native 系统用的是 powerd 自己的调度路径）。
- 裸 `echo mem` 绕过了 powerd，唤醒源矩阵可能未按 Kindle 期望配置（电源键唤醒在这条路径上也失效，说明 wakeup 源注册和 powerd 的 suspend 流程强耦合）。

未再尝试的替代方向（按可信度排序）：
1. 用 rtc2（SNVS RTC）闹钟代替 rtc0 重试；
2. `busybox rtcwake -d /dev/rtc0 -m mem -s N`（同 alarm 机制，成功率存疑）；
3. 放弃裸挂起，改用 powerd 原生休眠（`preventScreenSaver 0` + 缩短 powerd 自动休眠计时），电源键唤醒可靠，但唤醒时机不受 daemon 控制；
4. 接受现状：插电场景一律 MODE=ac。

### kindle-dash 原文机制为何不能照搬

它面向的旧款 Kindle（Paperwhite 时代）用 mxc_rtc 平台设备，`wakeup_enable` 节点直接收"秒数"；Oasis 3 是 max77796 PMIC RTC + SNVS，节点都不存在。它的 `echo mem` 能工作还依赖停止 framework 后 powerd 不再插手，我们不停 framework。

切换：改设备上 `config` 的 `MODE=ac|battery`（或 kd.py 重新推 config），下一轮生效，无需重启 daemon。

## 健壮性

- 单实例：`flock -n -x` 持有 `.lock`（fd 9，进程生命周期；跨进程互斥已在本机实测），拿不到锁直接退出。
- 日志：`daemon.log`，每次写日志检查大小，>200KB 裁剪保留末尾 100KB。
- 信号：TERM/INT trap 清 pidfile、回滚 preventScreenSaver。
- 被强杀（kill -9）残留：`.lock` 由 flock 内核态持有，进程死锁自动释放，无残留问题；pidfile 残留由 start.sh 的 kill -0 检查兜底。
- 一键拉起：PC 侧 `python daemon/kd.py start`（幂等：先推脚本，已在跑则直接报状态）。设备侧兜底 `/mnt/us/qoder/daemon/start.sh`，以及书架 scriptlet `documents/q09-daemon.sh`（点书即拉起）。
- 设备重启后一切运行态消失（dropbear/telnetd/iptables/daemon 全没）：`kd.py start` 一键重建。fbink 路径 `/mnt/us/libkh/bin/fbink` 是持久分区，重启不丢。

## 运维速查

```bash
python daemon/kd.py start                # 部署+启动（幂等）
python daemon/kd.py status               # 进程/配置/电量/日志尾巴
python daemon/kd.py push out/card.png    # 原子推送，下一轮刷出
python daemon/kd.py push out/card.png --full   # 推送并要求下一轮全刷
python daemon/kd.py stop | restart | log
```

设备重启后（一切运行态消失）：书架点 "Qoder Run 08"（恢复 telnetd + dropbear 2222 + iptables）→ PC 侧 `python daemon/kd.py start`。设备在手边没有 PC 时：书架点 "q09-daemon"（scriptlet，直读 /mnt/us/qoder/daemon/start.sh）。

## 状态清单（2026-10-16）

已验证（真机）：
- ac 模式常驻：preventScreenSaver=1、60s 周期 GL16 局部刷、每 6 轮 GC16 -f 全刷、启动首刷全刷
- 内容契约：原子推送（tmp+mv）→ 下一轮刷出（changed=1）；meta force_full 消费后自动清零；meta waveform 覆盖局部波形（代码路径在，真机只验了 GL16/GC16）
- stop/start/status/log/push 全链路；重复 start 幂等；flock 拒绝第二实例（真机实测 rc=1）
- 日志轮转逻辑在（未自然触发过 200KB 阈值）
- RTC 硬件事实：rtc0/rtc1=max77796、rtc2=SNVS；rtc0 wakealarm 可写/可读/可取消（清醒状态实测）；/sys/power/state 含 mem

推断（未真机验证）：
- 日志轮转的实际效果；meta waveform 用 GL16/GC16 以外波形的显示效果
- fbink 对不支持波形的 AUTO 降级行为

实测失败（勿用）：
- battery 模式：mem 挂起后 RTC 闹钟（rtc0 wakealarm 写入成功）与电源键均无法唤醒，需强制重启。详见电源考证一节。
