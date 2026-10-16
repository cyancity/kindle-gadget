# kindle-gadget

目标：把一台越狱 Kindle 变成 agent 推送的墨水屏看板（herdr 里任意 agent 出内容 → 渲染 → 上屏）。前序工作由 qoder 会话 be002b57（2026-10-05/06）完成，本文件是该会话结束后核实过的设备事实。

## 设备

- Kindle Oasis 3（第 10 代，2019，国行 8GB Wi-Fi），序列号 G000WLxxxxxxxx（已脱敏），devcode 0WL，带广告版
- 固件 5.18.2（该机型 last_firmware，产品线已冻结；5.16.5 是 release_notes 残留文件的误导）
- 屏幕 1264×1680，300ppi，帧缓冲 8bpp 灰度，rotate 0 原生竖屏（`eips -i` 实测；`fbink -e` 会段错误，禁用）
- RAM 实测 482MB（MemTotal 493696 kB），root home 是 /tmp/root 不是 /root

## 越狱状态（已完成并验证）

- 方案 SpiderCat（azw3 侧载点开），jb.sh v2.2.1，回执 `documents/JAILBROKEN.txt` + `privesc_marker.txt`（uid=0）
- 只打了 userstore，不碰 rootfs，重启不丢；不写 rootfs（10 代 secure boot，无救砖手段）
- scriptlet 通道可用：`documents/*.sh` 被索引成书，点开以 root 执行（SpiderCat 已自带 sh_integration，不需要 hotfix）
- scriptlet 限制：60 秒硬超时（长任务要 setsid 脱离）；默认把 stdout 用 fbink 刷屏（画图脚本头部必须 `# DontUseFBInk`）；cwd 不定（首行 `cd "$(dirname "$0")"`)
- 设备上已有：/mnt/us/libkh/bin/fbink（1.25.0 全功能版）、/var/local/kmc/sbin/kpm.sh、busybox telnetd；无 dropbear/sshd/python/perl，有 lua/eips
- KOReader 已安装（/mnt/us/kmc/kpm/packages/koreader/，35.1M，含 dropbear；2026-10-16 实测可用，启动方式 `kpm launch koreader` 待试）

## 渲染链路（已验证全通一次）

HTML 卡片 → Chrome headless 截图 1264×1680 → Pillow 8bit 灰度 16 阶 Floyd–Steinberg → PNG 拷入设备 → 设备上 `fbink -q -W GC16 -f -g "file=/mnt/us/qoder/card.png"` 全刷上屏。用户已亲眼确认上屏效果。
本仓库：render.py（出图）、cards/、out/、rpc.py、tk.py、cmds/、scriptlets/。

## root shell（已打通，2026-10-16）

- 电脑和 Kindle 在同一路由器（YOLO）的**无线侧**即通：电脑连 Wi-Fi 后隔离消失（隔离只存在于路由器有线↔无线之间）。Clash TUN 不抢同网段流量（已验证）
- 设备 IP `192.168.1.189`（示例值，脚本可用环境变量 KINDLE_HOST 覆盖；MAC 7C-D5-66-xx-xx-xx 已脱敏）。插 USB（U 盘模式）时 Wi-Fi 会挂起，拔线后恢复
- **SSH（主通道）**：`ssh -i ~/.ssh/kindle -p 2222 root@192.168.1.189`，仅密钥。dropbear（KOReader 自带二进制，2022+ 版）以 `/mnt/us/koreader` 为 CWD 启动：`cd /mnt/us/koreader && dropbear -R -s -p 2222`
- 坑：这台 dropbear 读 **`/mnt/us/koreader/settings/SSH/authorized_keys`**（KOReader 惯例路径），不是 `/tmp/root/.ssh/`；`/tmp/root`（passwd 里的 root home）出厂 2770 组可写会让 dropbear 静默拒绝，需 `chmod 2700 /tmp/root`
- **telnet（备用）**：23 端口，busybox telnetd 直接 root 无认证。客户端用本仓库 telnet_run.py（stdin 传命令，`python telnet_run.py - < cmd.txt`）
- 设备上没有 sftp-server 和 scp 远端，传文件用 ssh 管道：`cat f.png | ssh ... "cat > /mnt/us/qoder/card.png"`
- 以上通道（telnetd/dropbear/iptables/chmod）**开机自启已部署并经两次真机重启验证**（2026-10-16、2026-10-17 00:43）：emergency.sh → qoder/autostart/autostart.sh 自动恢复网络通道并经 hooks.d 拉起看板 daemon，无需再点书架上的 "Qoder Run 08"（保留作手动兜底）。dropbear 主机密钥每次重启会变，ssh 报 HOST KEY 已变时 `ssh-keygen -R "[IP]:2222"` 清旧指纹再连
- **开机自启（已部署并经两次真机重启验证，2026-10-16 / 2026-10-17 00:43）**：走 SpiderCat 官方钩子 `/mnt/us/emergency.sh`（由 rootfs 上的 upstart job `/etc/upstart/kmc.conf` 在 framework_ready 时以 root 执行；appreg.db 里另有 org.kindlemodding.emergency_launcher 冗余触发）。它转调 `/mnt/us/qoder/autostart/autostart.sh`（幂等：iptables 查重插入、telnetd/dropbear 查监听再启动、chmod 2700 /tmp/root），并经 `qoder/autostart/hooks.d/` 拉起看板 daemon。机制考证见 `autostart/DESIGN.md`；部署用 `autostart/deploy.sh`（--check/--smoke/--status）
- 渲染上屏：`python render.py cards/xxx.html -o out/xxx.png`（不能加 -I，Pillow 在用户 site-packages）→ ssh 管道推送 → `fbink -q -W GC16 -f -g "file=/mnt/us/qoder/card.png"`。2026-10-16 已验证全无线闭环，卡片 cards/002-wifi-channel.html
- **fb 截图（rotate=3 横屏）**：`cat /dev/fb0` 取 1696×2560@8bpp（stride 1696），横屏可见画面就是 dump 顶部一条**正立的 1680×1264 横带**，直接 crop(0,0,1680,1264)，不要旋转（2026-10-17 实测定案；早前"裁完再 ROTATE_90"的说法是错的）。竖屏 crop(0,0,1264,1680)。工具化：screenshot.py

## 看板 daemon（2026-10-16 落地并验证）

- 设备侧 `/mnt/us/qoder/daemon/`（dashboard.sh/start.sh/stop.sh/config/current.png/meta/daemon.log），repo 侧 `daemon/`（kd.py + device/ + DESIGN.md）
- PC 控制：`python daemon/kd.py start|stop|status|restart|log|push`；push 是 tmp+mv 原子替换，`--full` 置 meta force_full=1
- ac 模式（默认，插电常驻）：preventScreenSaver=1 + 60s 轮询，GL16 局部刷、每 6 轮 GC16 -f 全刷、启动首刷全刷；config 每轮重读，改配置不用重启
- 重启设备后恢复：书架点 "Qoder Run 08"（实测 2026-10-16：telnetd + dropbear 2222 + iptables 全回来）→ `python daemon/kd.py start`；设备手边没 PC 时点书架 scriptlet "q09-daemon"（documents/q09-daemon.sh，是否已索引成书未验证）
- **battery 模式（suspend+RTC 唤醒）实测失败勿用**：写 rtc0 wakealarm rc=0 + `echo mem` 挂起后，RTC 闹钟和电源键都唤不醒，只能长按重启（2026-10-16 实录，用户在场才脱困）；kindle-dash 的 mxc_rtc/wakeup_enable 节点这台机器没有（它面向旧款）。细节见 daemon/DESIGN.md

## 待办

- herdr 对接：任意 agent 产 HTML → 渲染推送
- 探索 KOReader 启动（kpm launch koreader）
- 用量卡定时自动刷新（daemon 侧小时级触发，现为 Studio 按钮/CLI 手动）
- battery 模式替代方案（rtc2/rtcwake/powerd 原生 suspend）：各自失败都要重启才能脱困，单独立项

## 教训

- 一次拔线周期打包一批命令，减少用户来回插拔
- 不要并发跑两个写同一文件的安装
- FBInk 参数以设备 `fbink --help` 和源码为准，不要凭记忆
- 裸 `echo mem > /sys/power/state` 在这台 5.18.2 上是"单程票"：RTC 闹钟唤不醒、电源键唤不醒，只能长按强制重启。挂起类实验必须先确认用户在场
- ssh 远端脚本里避免用 `. file` source 可能不存在的文件（ash 里是 fatal，整个命令 rc=2 直接断）
