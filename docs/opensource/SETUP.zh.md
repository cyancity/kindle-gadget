# 配置教程：越狱后的完整工具链

> **适用范围**：本教程实测机型：Kindle Oasis 3（第 10 代）+ 固件 5.18.2 + SpiderCat（jb.sh v2.2.1），PC 侧为 Windows 11 + Git Bash + Python 3.14。其他机型、固件或 PC 系统仅作参考。前置条件：已按 [JAILBREAK.zh.md](JAILBREAK.zh.md) 完成越狱（有 root、有 scriptlet 通道）。
>
> **安全声明**：越狱风险自担，非官方支持。本教程面向你自己拥有且已过保的设备。设备上会开一个仅限密钥的 SSH 端口和一个无认证的 telnet 端口（仅限家庭内网使用，公网环境不要照做）。

[English](SETUP.en.md)

## 目录

1. [网络准备](#1-网络准备)
2. [PC 工具链](#2-pc-工具链)
3. [第一条 root 通道：scriptlet](#3-第一条-root-通道scriptlet)
4. [KOReader 与 SSH 通道](#4-koreader-与-ssh-通道)
5. [文件传输](#5-文件传输)
6. [渲染与推送](#6-渲染与推送)
7. [telnet 备用通道](#7-telnet-备用通道)
8. [看板 daemon](#8-看板-daemon)
9. [开机自启](#9-开机自启)
10. [重启后的世界](#10-重启后的世界)
11. [故障排查速查表](#11-故障排查速查表)
12. [卸载与还原](#12-卸载与还原)

约定：下文用 `192.168.1.189` 作为设备 IP 示例（本仓库脚本里的默认值），换成你自己的。仓库脚本都认环境变量 `KINDLE_HOST`，`export KINDLE_HOST=你的设备IP` 即可全局覆盖，不用改代码。所有 PC 侧命令在 Git Bash 里执行。

## 1. 网络准备

### 1.1 设备和 PC 必须在同一 Wi-Fi 的无线侧

- 设备：Kindle 设置 → Wi-Fi，连上你家路由器。
- PC：**也连这个 Wi-Fi**。很多路由器默认隔离「有线口 ↔ 无线客户端」，PC 走有线时 SYN 会被丢，设备侧一切正常也连不上（根因分析见 JAILBREAK.zh.md 踩坑实录 6.2）。
- 代理软件开 TUN 模式的：先确认流量没被虚拟网卡接走（`Find-NetRoute -RemoteIPAddress 192.168.1.189`，出接口是物理网卡才对）。同网段流量一般不抢（见踩坑实录 6.1）。

### 1.2 找到设备 IP

- 设备上：设置 → Wi-Fi → 已连接的网络，直接显示 IP。
- 或 PC 上扫 ARP 表（Kindle 的 MAC 前缀是 Amazon Lab126 的 `7C-D5-66`）：

  ```bash
  ping -n 1 192.168.1.255        # 先戳一下广播域（Git Bash 里 -n 可能要换成 -c）
  arp -a | grep -i 7c-d5-66
  # 本机输出形如：192.168.1.189      7c-d5-66-xx-xx-xx     动态（后三段被本教程打码）
  ```

验证连通性用 ARP 和 ssh，不要用 ping（设备防火墙可能丢 ICMP，且代理 TUN 会干扰 ping 的判断）。

### 1.3 休眠与 USB 模式的行为（先记住，少踩坑）

- **插 USB = U 盘模式**：`/mnt/us` 从设备侧摘除、交给主机，设备自己看不到里面的文件，Wi-Fi 同时挂起。拔线后恢复。所以开发节奏是「插线写文件 → 拔线执行 → 插线读日志」，一次拔线周期尽量打包一批命令。
- **休眠冻结一切**：设备一睡就关 Wi-Fi、冻结用户进程，所有通道静默。按电源键唤醒，或用 scriptlet 设置防屏保（第 3 节的 Net Mode 脚本带 60 分钟保活）。
- 设备事实（本机实测）：屏幕 1264x1680 / 300ppi / 8bpp 灰度帧缓冲 / 原生竖屏 rotate 0（`eips -i` 实测；`fbink -e` 会段错误，禁用）；RAM 482MB（MemTotal 493696 kB）；root 的 home 是 `/tmp/root` 不是 `/root`；内核 4.1.15-lab126；busybox 1.34.1。

## 2. PC 工具链

### 2.1 Python + Pillow

```bash
python --version          # 本机 3.14；3.10+ 均可
python -c "import PIL; print(PIL.__version__)"
# 没有则安装（本机 Pillow 装在用户 site-packages，render.py 不能加 -I 运行）
python -m pip install --user Pillow
```

### 2.2 浏览器

render.py 依次找 `C:\Program Files\Google\Chrome\Application\chrome.exe` 和 `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`，任一存在即可。其他安装位置或非 Windows 系统，改 render.py 顶部的 `CHROME` 列表。

### 2.3 SSH 密钥（dropbear 用 RSA）

```bash
ssh-keygen -t rsa -m PEM -b 2048 -N "" -f ~/.ssh/kindle
```

- `-m PEM`：老格式私钥。设备上的 dropbear 来自 KOReader（2022+ 版本），ed25519 支持未在本机验证过，RSA PEM 是实测可用路径。
- 私钥 `~/.ssh/kindle` 不进任何仓库；公钥 `~/.ssh/kindle.pub` 马上要写进设备。

验证 Git Bash 里有 ssh：

```bash
ssh -V
```

### 2.4 字体（可选，影响卡片观感）

- Studio 界面：仓库自带 Inter（OFL，`studio/vendor/fonts/`），装不装都正常显示。
- 卡片默认字体栈：标题 `"Anthropic Sans", "Inter", sans-serif`；数字/英文 JetBrains Mono；中文 思源宋体（Noto Serif SC / Noto Sans SC）。三个都是 OFL，装上后渲染产物才和文档截图一致：
  - Inter：https://github.com/rsms/inter/releases
  - JetBrains Mono：https://www.jetbrains.com/lp/mono/
  - 思源宋体/黑体：https://github.com/notofonts/noto-cjk（或 Google Fonts）
  - JetBrains Mono 与思源系列不装也能跑，浏览器会回退到系统等宽/宋体，仅观感有差。
- Anthropic Sans 是 Anthropic 的专有字体（仅限个人使用授权），**不随本仓库分发**，也没放进任何 vendor 目录。你在自己机器上自行安装后，标题会自动用它；没装就回退 Inter。

### 2.5 Studio（网页工作台，可选）

```bash
python studio/server.py    # 只起本地服务，浏览器开 http://127.0.0.1:8762
pip install pystray && python studio/tray.py   # 或：托盘常驻（右下角图标）
```

功能：卡片 HTML 编辑（CodeMirror 高亮）、真实渲染预览（预览图就是 render.py 的产物，带 Oasis 设备壳、横竖屏切换）、一键推送、卡片版本管理（每次保存自动存档）、深浅两主题。圈注模式可以把截图区域+要求发给本地 Agent 领单改稿（`POST /api/agent-task` 落单，`GET /api/agent-task?claim=1` 领单，`POST /api/agent-result` 回填；契约见 `docs/STUDIO.md`）。服务只绑 127.0.0.1，不对外。

## 3. 第一条 root 通道：scriptlet

### 3.1 机制（先懂再点）

SpiderCat 自带 sh_integration：`documents/` 里任何 `.sh` 会被索引成书，点开即以 **root** 执行。四条硬约束：

- **60 秒硬超时**：超时进程被 kill -9。长任务必须 `setsid` 脱离到后台，让 scriptlet 秒退。
- **stdout 默认刷屏**：脚本输出会经 FBInk 打到屏幕上（先清屏再从第 5 行开始写）。要画图的脚本头部必须写 `# DontUseFBInk`，否则自己的输出会盖掉画面。
- **工作目录不定**：首行写 `cd "$(dirname "$0")"`。
- **头部只有 4 个字段**：`# Name:`、`# Author:`、`# Icon:`、`# UseHooks` 或 `# DontUseFBInk`。

### 3.2 造一本「Net Mode」书

下面的脚本一次做完：放行防火墙 23/2222、起 telnetd、写 authorized_keys、修 `/tmp/root` 权限、起 dropbear、防屏保保活 60 分钟。KOReader 没装时 dropbear 那步会失败，其余照常生效，装好后再点一次即可补上。

把内容存成 `netmode.sh`（**必须 LF 行尾**，见下方注意），把 `PUBKEY` 换成你 `~/.ssh/kindle.pub` 的内容（一整行）：

```sh
#!/bin/sh
# Name: Net Mode
PUBKEY='ssh-rsa AAAA...换成你~/.ssh/kindle.pub的完整内容'
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

脚本说明（为什么这么写）：

- 设备默认防火墙策略是 `-P INPUT DROP`，入站 23/2222 必须显式放行；`-C` 查重避免重复点击累积规则。
- `chmod 2700 /tmp/root`：dropbear 发现 root home 组可写（出厂 2770）会**静默拒绝认证**，这一步不加，SSH 永远 Permission denied。
- dropbear 必须以 `/mnt/us/koreader` 为工作目录启动（它按 CWD 解析路径），authorized_keys 固定读 `/mnt/us/koreader/settings/SSH/`（KOReader 惯例路径），不是 `/tmp/root/.ssh/`。
- `-R` 自动生成主机密钥，`-s` 关密码登录（仅密钥），端口 2222。
- 防屏保只挡屏保不挡深睡，60 秒重新声明一次能撑住清醒时间；60 分钟后自动归还。

**LF 行尾注意**：Git Bash 下用 `vim`/`nano` 或 `printf` 写这个文件都行；用 Windows 编辑器写完要在 Git Bash 里确认行尾：

```bash
file netmode.sh           # 期望输出含 "with very long lines" 且无 "CRLF"
# 若是 CRLF：sed -i 's/\r$//' netmode.sh
```

### 3.3 部署并执行

1. USB 连接 Kindle，把 `netmode.sh` 拷进 `documents\`。
2. 安全弹出。在 Kindle 上下拉刷新图书馆，书库里会出现 **Net Mode**。
3. 点开它。预期：屏幕闪一下显示 `NET_MODE_STARTED`（scriptlet 把 stdout 刷上屏），然后回主页。
4. 拔线状态下设备保持醒着（保活循环在跑）。

### 3.4 验证 telnet 通了

PC 上（仓库根目录）：

```bash
python -I telnet_run.py "id"
```

预期输出含：

```
uid=0(root) gid=0(root)
```

失败排查：`arp -a | grep -i 7c-d5-66` 看设备在不在；不在就是睡了或 Wi-Fi 断了，按电源键唤醒再试；MAC 在但连不上，按 JAILBREAK.zh.md 踩坑实录 6.1/6.2 查 TUN 和路由器隔离。

## 4. KOReader 与 SSH 通道

### 4.1 安装 KOReader（单进程！）

经 telnet 执行（或书库里再点一次 Net Mode 前先装）。设备要联网，下载约 41MB，需要几分钟：

```bash
python -I telnet_run.py "sh /var/local/kmc/sbin/kpm.sh install koreader; echo rc=\$?"
```

等待期间**不要**再点任何会触发 kpm 的东西，不要插拔 USB。官方等价路径是搜索框 `;kpm install koreader`（本机未走这条，用的是 scriptlet + kpm.sh，两者等价）。

验证（本机实测值）：

```bash
python -I telnet_run.py "ls /mnt/us/kmc/kpm/packages/koreader/koreader/dropbear && du -sh /mnt/us/kmc/kpm/packages/koreader/"
# 预期：/mnt/us/kmc/kpm/packages/koreader/koreader/dropbear
#       约 35.1M
```

历史教训：两个 kpm 并发写同一个临时 kpkg 会双双拿到截断的包，安装损坏（JAILBREAK.zh.md 踩坑实录 6.5）。同一时间只允许一个 kpm 进程。

### 4.2 启动 dropbear 并验证 SSH

KOReader 装好后，再点一次书架上的 **Net Mode**（幂等，会补上 dropbear），或经 telnet 手动执行：

```bash
python -I telnet_run.py "chmod 2700 /tmp/root; mkdir -p /mnt/us/koreader/settings/SSH; cp /mnt/us/qoder/pubkey.txt /mnt/us/koreader/settings/SSH/authorized_keys; chmod 600 /mnt/us/koreader/settings/SSH/authorized_keys; cd /mnt/us/koreader && /mnt/us/kmc/kpm/packages/koreader/koreader/dropbear -R -s -p 2222 && echo DROPBEAR_OK"
```

PC 上验证：

```bash
ssh -i ~/.ssh/kindle -p 2222 -o StrictHostKeyChecking=no root@192.168.1.189 id
# 预期：uid=0(root) gid=0(root)
```

至此可以 `exit` 掉 telnet 的心思了，SSH 是主通道（仅密钥、端口 2222），telnet 留作备用。

SSH 失败排查速查：

| 症状 | 原因 | 修复 |
|---|---|---|
| Permission denied | authorized_keys 路径不对（写到 `/tmp/root/.ssh/` 了） | 必须是 `/mnt/us/koreader/settings/SSH/authorized_keys` |
| Permission denied | `/tmp/root` 还是出厂 2770（组可写） | `chmod 2700 /tmp/root` |
| Permission denied | 私钥格式不对 | 用 `ssh-keygen -t rsa -m PEM` 重签 |
| TCP 通但立刻断 | dropbear 不在跑，或 CWD 不对 | 必须 `cd /mnt/us/koreader` 后再启动 |
| 连接超时 | 设备睡了 / Wi-Fi 断 / TUN 抢路由 | 见第 1 节和踩坑实录 |

## 5. 文件传输

设备上没有 sftp-server，scp 也没有远端。一切走 ssh 管道：

```bash
cat out/card.png | ssh -i ~/.ssh/kindle -p 2222 root@192.168.1.189 "cat > /mnt/us/qoder/card.png"
```

传多个文件就多条管道，目标目录先建：

```bash
ssh -i ~/.ssh/kindle -p 2222 root@192.168.1.189 "mkdir -p /mnt/us/qoder/autostart/hooks.d"
cat autostart/autostart.sh | ssh -i ~/.ssh/kindle -p 2222 root@192.168.1.189 "cat > /mnt/us/qoder/autostart/autostart.sh"
```

Git Bash 特有坑：以 `/` 开头的**独立参数**会被 MSYS 改写成本机路径（`/mnt/us/x` 变成 `C:/Program Files/Git/mnt/us/x`）。写进引号内的远端命令串不受影响；`push.py` 的 `--path` 参数做了自动修复，裸 ssh 命令时把远端路径放进引号里即可。

Windows 行尾坑：从 PC 推脚本到设备一律先去掉 CR（`tr -d '\r' < f.sh | ssh ... "cat > ..."`），CRLF 会让 ash 报奇怪的错误。`autostart/deploy.sh` 已内置这一步。

## 6. 渲染与推送

### 6.1 渲染链

```
HTML 卡片 → Chrome headless 截图 1264x1680 → Pillow 8bit 灰度
  → 16 阶 MEDIANCUT 量化 + Floyd–Steinberg 抖动 → PNG
```

```bash
python render.py cards/push-test-hello.html -o out/test.png
# 预期输出形如：out/test.png  1264x1680  mode=L  bytes=52718
```

注意：render.py **不能加 `-I` 运行**（Pillow 在用户 site-packages，`-I` 会隔离掉）。

### 6.2 卡片 HTML 约束

1264x1680 固定尺寸；不要用 flex 的 `gap`、`position: sticky/fixed`、动画（墨水屏和截图都会翻车）；字号 ≥30px；用系统字体；白底黑字，避免细小彩色元素（最终只有 16 阶灰度）。现成模板见 `cards/`。

### 6.3 推送（一条命令）

```bash
python push.py cards/push-test-hello.html            # 渲染 → 传输 → GC16 全刷（黑闪一次）
python push.py cards/push-test-hello.html --partial  # GL16 局刷，无黑闪，适合小改
python push.py out/xxx.png                           # 已有 PNG 直接推
```

预期输出：

```
已渲染: push-push-test-hello.png
已传输: push-push-test-hello.png -> 192.168.1.189:/mnt/us/qoder/card.png
已刷屏: GC16 全刷
```

屏幕上出现卡片即全链路打通。给 agent 的完整调用契约（参数、出错自查、硬约束）见仓库根目录 `push.md`。

### 6.4 FBInk 手动刷屏（调试用）

```bash
ssh -i ~/.ssh/kindle -p 2222 root@192.168.1.189 \
  '/mnt/us/libkh/bin/fbink -q -W GC16 -f -g "file=/mnt/us/qoder/card.png"'
```

- 全刷（去残影）：`-W GC16 -f`；局刷（无黑闪）：`-W gl16`（不带 `-f`）。
- 波形以设备 `fbink --help` 为准（本机 1.25.0 支持 A2/DU/GL16/GC16/GC16_FAST/GL16_FAST/REAGL/REAGLD/GCK16/GLKW16/GCC16/GLRC16），不支持的模式会降级 AUTO（降级行为未验证）。
- `fbink -e` 在本机段错误，禁用；取屏幕参数用 `eips -i`。

## 7. telnet 备用通道

SSH 挂了的时候的兜底（busybox telnetd，root 无认证，**只在内网用**）：

```bash
python -I telnet_run.py "id"                    # 单条命令
python -I telnet_run.py - < cmds.txt            # 批量：cmds.txt 里写多行命令
TELNET_DEBUG=1 python -I telnet_run.py "uname -a"   # 带调试输出
```

telnetd 重启即消失，Net Mode / autostart 会重新拉起。安全上它等价于「你家局域网里一个免密 root 后门」，家庭网络可接受，公共网络不要开。

## 8. 看板 daemon

daemon 常驻设备侧，把 `/mnt/us/qoder/daemon/current.png` 周期刷上屏；PC 侧随时推新图，下一轮自动刷出。默认 ac 模式（插电常驻）。

### 8.1 启动与控制（PC 侧）

```bash
python daemon/kd.py start                # 部署脚本到设备 + 启动（幂等）
python daemon/kd.py status               # 进程/配置/电量/日志尾巴
python daemon/kd.py push out/test.png    # 原子推送（tmp+mv），下一轮刷出
python daemon/kd.py push out/test.png --full   # 推送并要求下一轮全刷
python daemon/kd.py log -n 30            # 看日志
python daemon/kd.py stop | restart
```

`start` 预期输出含 `started pid=...`，随后 status 显示 `daemon: RUNNING pid=...`。设备失联时 start 会报 `[kd] 设备失联`，先查第 1 节。

### 8.2 刷新纪律

- 60 秒一轮：GL16 局部刷；每 6 轮、启动首刷、`meta force_full=1` 时 GC16 `-f` 全刷。
- 推送是原子的（先写 `.tmp` 再 `mv`），推到一半不会刷出半张图。
- 设备上 `config` 每轮重读，改配置不用重启：`MODE=ac`、`INTERVAL=60`、`FULL_EVERY=6`、`REDRAW_UNCHANGED=1`。
- `meta` 文件可临时覆盖：`force_full=1`（下一轮全刷后自动清零）、`waveform=GC16`（覆盖局刷波形，白名单校验）。

### 8.3 battery 模式：实测失败，勿用

config 里有 `MODE=battery`（休眠 + RTC 唤醒），**2026-10-16 真机实测失败**：挂起后 RTC 闹钟（rtc0 wakealarm 写入成功）和电源键都唤不醒，只能长按强制重启。kindle-dash 的 mxc_rtc 节点这台机器没有（它面向旧款）。细节与未验证的替代方向见 `daemon/DESIGN.md`。插电场景一律 `MODE=ac`。

### 8.4 验证清单（本机已实测）

- ac 模式常驻：preventScreenSaver=1、GL16 局刷、每 6 轮 GC16 全刷、启动首刷全刷
- 原子推送下一轮刷出；`--full` 置 meta 并被消费
- stop/start/status/log/push 全链路；重复 start 幂等；flock 拒绝第二实例

## 9. 开机自启

### 9.1 机制（考证全文见 `autostart/DESIGN.md`）

SpiderCat 越狱在 rootfs 上留了一个 upstart job `/etc/upstart/kmc.conf`（`start on framework_ready`），其 pre-start 检查 `/mnt/us/emergency.sh`，存在则 chmod +x 后以 root 执行；appreg.db 里的 `org.kindlemodding.emergency_launcher` 是冗余触发。这是作者留给用户的唯一 rootfs 外 boot 钩子，零 rootfs 写入。pre-start 会阻塞到脚本退出，所以钩子必须秒级返回、幂等。

本项目的链路：

```
/etc/upstart/kmc.conf (framework_ready)
  -> /mnt/us/emergency.sh            3 行引导
  -> /mnt/us/qoder/autostart/autostart.sh   全部逻辑（幂等）
       iptables 放行 23/2222（-C 查重）
       telnetd 0.0.0.0:23（查监听再起）
       chmod 2700 /tmp/root
       dropbear -R -s -p 2222（CWD=/mnt/us/koreader）
       hooks.d/*.sh 逐个 setsid 拉起（stdout 进 hooks.log）
```

### 9.2 部署

```bash
cd autostart
./deploy.sh            # 部署 emergency.sh + autostart.sh 到设备并做语法检查
./deploy.sh --check    # 只做语法检查（SYNTAX_OK）
./deploy.sh --smoke    # 手动跑一次 autostart.sh 并打印日志（幂等，可连跑验证）
./deploy.sh --status   # 监听端口 + iptables 规则 + /tmp/root 权限 + 日志尾巴
```

部署脚本自动 `tr -d '\r'` 处理 Windows 行尾。

### 9.3 验证状态

```bash
./deploy.sh --status
# 预期含：
#   netstat: 0.0.0.0:23 与 0.0.0.0:2222 各一条 LISTEN
#   iptables: dpt:23 与 dpt:2222 各恰好一条 ACCEPT（重复跑不累积）
#   /tmp/root 权限 2700
#   autostart.log 尾部有 === autostart invoked / done
```

**未完成**：真实重启触发链尚未验证（emergency.sh 由 framework_ready 拉起的那一跳）。部署后的重启验证方案（判定标准、排查顺序、兜底）已写在 `autostart/DESIGN.md` 第 4、5 节，照做即可。

### 9.4 接入自己的开机任务

把可执行 `.sh` 放进设备 `/mnt/us/qoder/autostart/hooks.d/`，每次开机被 autostart.sh 以 root + setsid 拉起，stdout/stderr 进 `hooks.log`。要求脚本自己 daemonize 或快速 background。看板 daemon 的 hook（`dashboard.sh`）已预留接口、尚未实现（见 INDEX.md）。

## 10. 重启后的世界

设备重启后一切运行态消失：telnetd、dropbear、iptables 规则、`chmod 2700 /tmp/root`、daemon 全没了。持久分区上的东西都在：`/mnt/us` 全部脚本与日志、fbink 二进制、authorized_keys、KOReader、越狱本身。

恢复手段，按优先级：

1. **autostart 生效后**（重启验证通过后）：什么都不用做，开机自动回来。
2. **书架点 Net Mode（或 Run 08）**：一秒恢复 telnet + SSH + 防火墙 + 60 分钟保活。然后 PC 上 `python daemon/kd.py start` 把 daemon 拉起来。
3. **设备在手边没 PC**：书架点 scriptlet `q09-daemon`（`documents/q09-daemon.sh`，直读 `/mnt/us/qoder/daemon/start.sh`；是否已被索引成书未验证）。

重启命令（已核对）：首选 `/sbin/reboot`；备选 `lipc-set-prop com.lab126.powerd deviceRestart 1`（属性实测存在）。注意 MobileRead 上常见的 `lipc-set-prop com.lab126.cmd reboot do` 在本机**不可用**（`lipc-probe com.lab126.cmd` 没有 reboot 属性）。

## 11. 故障排查速查表

| 症状 | 先查 | 判定与动作 |
|---|---|---|
| SSH/telnet 全不通 | `arp -a \| grep -i 7c-d5-66` | ARP 有 = 设备活着，查路由/防火墙；ARP 无 = 睡了或 Wi-Fi 断，唤醒设备或点 Net Mode |
| ping 通但端口不通 | `Find-NetRoute -RemoteIPAddress <ip>` | 出接口是 TUN（Meta）就是代理抢路由，加主机路由或 route-exclude-address |
| 设备侧一切正常、PC 连不上 | PC 是否走有线 | 有线↔无线隔离，PC 连同一个 Wi-Fi |
| SSH Permission denied | 见 4.2 的表 | authorized_keys 路径 / chmod 2700 / 密钥格式 |
| 传输中断连 | 是否在往 `/mnt/us` 写时拔了线 | 拔线会摘走 `/mnt/us`，长任务必须在拔线状态跑完 |
| scriptlet 点了没反应 | 脚本是否秒退 | 60 秒超时强杀；长任务 `setsid` 脱离；画图脚本加 `# DontUseFBInk` |
| 刷屏命令没画面 | fbink 路径与参数 | 路径 `/mnt/us/libkh/bin/fbink`；`-g "file=路径"`；别用 `-e`（段错误） |
| kpm 安装损坏 | 是否并发 | 单进程重跑 `kpm.sh install koreader` |
| 屏幕残影 | 距上次全刷多久 | `fbink -q -W GC16 -f -g "file=..."` 手动全刷，或 `kd.py push --full` |
| daemon 没起来 | `python daemon/kd.py status` | 看 start 输出与 `daemon.log`；flock 单实例，第二实例直接退出 |

## 12. 卸载与还原

- **只还原运行态**（保留越狱）：重启一次即可，telnetd/dropbear/iptables/daemon 全清。不再需要自启时，删掉设备上的 `/mnt/us/emergency.sh`。
- **删除项目文件**：`/mnt/us/qoder/` 整目录、`/mnt/us/documents/` 里本项目的 `*.sh`；KOReader 想卸载的话用 kpm 的卸载命令（KPM 包带 uninstall 钩子，具体子命令名以 `kpm.sh` 帮助为准）。
- **彻底还原（清掉越狱）**：恢复出厂，见 JAILBREAK.zh.md 第 5.4 节（U 盘根目录放 `DO_FACTORY_RESTORE` 空文件重启）。
