# 开机自启机制：考证与设计

设备：KOA3 / FW 5.18.2 / SpiderCat (jb.sh v2.2.1)。硬约束：不写 rootfs（10 代 secure boot，写坏无救）。

## 1. 机制考证

### 候选 A（选定）：`/mnt/us/emergency.sh` —— SpiderCat 官方 boot 钩子

链路（设备实地核对 + 上游源码双重出处）：

1. rootfs 上存在 `/etc/upstart/kmc.conf`（SpiderCat 越狱时写入，ext3 只读挂载上持久存在）：
   upstart job，`start on framework_ready`，其 `pre-start` 检查 `/mnt/us/emergency.sh`，
   存在则 `chmod +x` 后以 **root** 执行 `/bin/sh`。设备上 `initctl list` 实测 `kmc start/running`。
2. `patch_system.sh`（jb.sh 的系统补丁段，`08_install_kmc_upstart.sh`）每次运行都会确保
   `/etc/upstart/kmc.conf` 在位（`make_mutable` → 拷贝 → `make_immutable`），双保险。
3. appreg.db 里另有 `org.kindlemodding.emergency_launcher` → `/bin/sh /mnt/us/emergency.sh`
   （framework 侧触发，与 upstart 互为冗余）。

出处：
- 设备实测：`/etc/upstart/kmc.conf` 全文、`initctl list`、`strings /var/local/appreg.db | grep emergency`
- 上游：github.com/KindleModding/jb.sh `src/kmc/system_patches/kmc.conf`、
  `src/kmc/sql/appreg_register_emergency.sql`

要点：
- 零 rootfs 写入：只往 userstore（/mnt/us，fuse 可写、可执行位有效）放文件。
- 触发时机是开机后 framework 就绪（framework_ready 是 stock 事件，十几个 stock job 都监听它）；
  待机唤醒不触发，正合需求。
- pre-start 会阻塞到脚本退出：钩子脚本必须秒级返回（telnetd/dropbear 自身 daemonize，iptables 秒级）。
- 作者设计语义是"救砖通道"，同时也是官方留给用户的唯一 rootfs 外 boot 钩子。

### 候选 B（否决）：KPM 包

KPM 包只有 `install.sh` / `uninstall.sh` / `launch.sh` 三个钩子，**没有 boot hook**
（官方文档 kindlemodding.org/kindle-dev/kpm/creating-a-package.html 明示；
launch.sh 只能由 launcher 用户触发）。KPM 定位是装包，不是自启。

### 候选 C（否决）：appreg.db 注册自定义 handler

仿照 `org.kindlemodding.hotfix_launcher` 往 /var/local/appreg.db 写自己的条目。
否决：schema 无文档、触发时机依赖 framework 内部行为、写坏 appreg.db 可能影响 framework 启动，
侵入度和风险都显著高于候选 A，收益为零（A 已覆盖同样场景）。

### 其他排查结论

- 改 /etc/upstart/ 加自己的 job：写 rootfs，禁止。
- scriptlet（documents/*.sh 点书执行）：需人工点击，不满足"自动"，保留为手动兜底（Run 08）。
- KUAL / MRPI：已废弃（ jb.sh v2.2.1 的 dispatch.sh 仅在装了 MRPI 时才走它；本机未装）。

## 2. 实现

| 位置 | 文件 | 作用 |
|---|---|---|
| 设备 | `/mnt/us/emergency.sh` | 3 行引导，转调 autostart.sh（保持救砖钩子轻量） |
| 设备 | `/mnt/us/qoder/autostart/autostart.sh` | 全部逻辑，幂等 |
| 设备 | `/mnt/us/qoder/autostart/hooks.d/` | 预留钩子目录，见下 |
| 设备 | `/mnt/us/qoder/autostart/autostart.log` | 每次执行的痕迹（上限 50K 自动截断） |
| repo | `autostart/autostart.sh`、`autostart/emergency.sh` | 源文件 |
| repo | `autostart/deploy.sh` | 部署/语法检查/冒烟/状态（`--check --smoke --status`） |

autostart.sh 做的事（与 Run 08 的网络部分等效，但幂等）：

1. iptables 放行入站 23/2222（先 `-C` 查重，不重复插入 —— Run 08 每点一次插一条，规则会累积）
2. `busybox telnetd -l /bin/sh`（0.0.0.0:23，仅在无监听时启动，不 kill 现有实例）
3. `chmod 2700 /tmp/root`（dropbear 对 root home 的组可写检查）
4. `cd /mnt/us/koreader && dropbear -R -s -p 2222`
   （二进制：`/mnt/us/kmc/kpm/packages/koreader/koreader/dropbear`；CWD 必须是 /mnt/us/koreader，
   设备实测运行中实例 `/proc/<pid>/cwd -> /mnt/us/koreader`；authorized_keys 在
   `/mnt/us/koreader/settings/SSH/authorized_keys`，userstore 持久，重启不丢）
5. hooks.d：遍历 `hooks.d/*.sh`，setsid 脱离执行

### 给看板 daemon 的接口（预留，未实现）

写 `/mnt/us/qoder/autostart/hooks.d/dashboard.sh`（repo 侧对应文件）即可，每次开机
autostart.sh 会以 root + setsid 把它拉起，stdout/stderr 进 `hooks.log`。
要求：脚本自己 daemonize 或快速 background，不要前台长跑（阻塞的是它自己，不是 autostart ——
setsid 已脱离，但仍会占一个 sh 进程）。

## 3. 已验证（不重启能做的都做了）

- `sh -n` 语法检查在设备上通过（deploy.sh --check）
- 手动跑一次 autostart.sh（`deploy.sh --smoke`）：等效 Run 08 网络部分的"已在位"分支
  （当前服务本来就在跑，预期全部走 already 路径），连续跑两遍验证幂等：
  iptables 规则数不增加、telnetd/dropbear 不被重复拉起、log 正常。
- 未验证（等重启）：emergency.sh 真实触发链。无法在不重启的前提下触发 framework_ready；
  "从零拉起 telnetd/dropbear"的分支也无法验证（红线禁止 kill 现有实例）。
  该分支调用的命令与 Run 08 / ssh_setup.sh 中已实战验证过的命令完全同款。

## 4. 重启验证方案（已批准待执行：等 leader 明确下令，未执行）

1. 执行重启。命令已核对：
   - 首选 `/sbin/reboot`（二进制实测存在；注：MobileRead 常见的
     `lipc-set-prop com.lab126.cmd reboot do` 在本机不可用 —— `lipc-probe com.lab126.cmd`
     实测无 reboot 属性，属性表只有网络相关）。
   - 备选 `lipc-set-prop com.lab126.powerd deviceRestart 1`（属性实测存在，write-only Int）。
2. 等 3~5 分钟（boot + framework_ready + Wi-Fi 回连 YOLO）。
3. 判定（`autostart/deploy.sh --status` 一条命令看全）：
   - SSH 2222 直接通（重启后不经任何人工步骤）→ dropbear + iptables + chmod 全链生效
   - `python -I telnet_run.py "id"`（仓库根目录）通 → telnetd 生效
   - `/mnt/us/qoder/autostart/autostart.log` 里有 reboot 之后时间戳的一次 `=== autostart invoked`
   - `iptables -L INPUT -n` 中 23/2222 各恰好一条 ACCEPT（无累积）
4. 若不通：按 §5 顺序排查；任何时候需要恢复通道，点书架 "Qoder Run 08"（§6）。

## 5. 重启后 SSH 不通的排查顺序（预演）

每一步都是"先取证再动手"，恢复通道优先，取证次之。已确认的取证手段：

| # | 检查 | 手段 | 判定 |
|---|---|---|---|
| 0 | 设备在网络层活着 | `arp -a | grep -i 7c-d5-66`（ping 可能被挡，以 ARP 为准） | ARP 有 = 设备起来了，IP 没变；ARP 无 = Wi-Fi 没回连或 IP 变了，看路由器 DHCP、或人到场看屏幕 |
| 1 | emergency.sh 被执行过 | `/mnt/us/qoder/autostart/autostart.log` 有无重启后时间戳（autostart.sh 第一行就写 log，这是触发链最直接的证据） | 见分支 A/B |
| 2 | kmc job 活着 | `initctl status kmc`（需先有通道） | 期望 `start/running` |
| 3 | kmc.conf pre-start 被跑过 | `grep "hello there from kmc" /var/log/messages`（f_log 走 `logger -t system`，落点已核实 /var/log/messages；注意重启后文件可能轮转，先看文件头时间戳） | 有这行 = upstart 触发链工作，问题在 emergency.sh 之后；没有 = kmc.conf 没被 upstart 执行 |
| 4 | kmc.conf 本体还在 | `ls -la /etc/upstart/kmc.conf && diff /etc/upstart/kmc.conf /var/local/kmc/system_patches/kmc.conf` | 缺失/不一致 → `RUN_MODE=1 sh /var/local/kmc/system_patches/run_patch.sh` 重装（patch_system.sh 会重拷） |

分支 A：log 有新记录但服务不通
→ autostart.sh 跑了但后半段出错，log 里会有 `FAILED` 行。SSH 2222 不通而 telnet 23 通时，
用 `python -I telnet_run.py "sh /mnt/us/emergency.sh; tail -30 /mnt/us/qoder/autostart/autostart.log"`
手动补一遍并看真实报错（常见嫌疑：dropbear 路径变更、/mnt/us/koreader 缺失、iptables 语法）。

分支 B：log 无新记录（emergency.sh 没被执行）
1. 先用 #3 区分是 upstart 没跑 kmc.conf，还是跑了但没找到 emergency.sh。
2. 若 kmc.conf pre-start 跑了（#3 有打点）而 emergency.sh 没动：第一嫌疑是
   **/mnt/us 挂载晚于 framework_ready**（设计上作者假设 userstore 先就位，但这是本方案
   唯一未经实测的时序假设）。预案（届时再实施）：把 autostart.sh 复制到 `/var/local`
   （可写、非 rootfs、开机即存在），emergency.sh 之外在 kmc.conf 无法改动的前提下改为
   依赖 appreg.db 的 `org.kindlemodding.emergency_launcher` 路径或 scriptlet 延迟自点。
3. 若 kmc.conf 根本没被跑（#3 无打点、#2 kmc job 不存在）：按 #4 重装 kmc.conf 后需再次
   重启才能验证（第二次重启仍需重新申请窗口）。

兜底纪律：任一步走不下去，点 "Qoder Run 08"（§6）恢复通道再继续；排查数据点记回本节。

## 6. 兜底：Run 08 与本方案的关系

书架 scriptlet "Qoder Run 08"（/mnt/us/documents/q08-run.sh → qoder/work.sh）保留不动：

- 它做的事（telnetd 重启 + iptables 插规则 + 防休眠保活 60 分钟 + eips 屏显）是本方案的
  超集（多一个防休眠保活），语义重叠但无冲突：Run 08 killall telnetd 后重启 telnetd，
  幂等性差一点（iptables 规则累积）但可正常工作。
- 本方案生效后 Run 08 的价值 = 防休眠保活 + 服务异常时的人工修复入口。
- autostart.sh 特意不做 preventScreenSaver（省电是看板 daemon agent 的职责域）。
