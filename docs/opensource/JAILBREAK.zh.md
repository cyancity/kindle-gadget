# 越狱教程：Kindle Oasis 3 + SpiderCat

> **适用范围**：本教程实测机型：Kindle Oasis 3（第 10 代，2019，国行 8GB Wi-Fi）+ 固件 5.18.2 + SpiderCat（jb.sh v2.2.1）。其他机型或固件仅作参考：方案选择、覆盖区间、命令输出都可能不同，动手前先到官方向导 kindlemodding.org 重新核对你自己的组合。
>
> **安全声明**：越狱是非官方修改，风险自担：可能变砖、失去保修、被 Amazon 封号（社区罕见但有先例）。本教程面向你自己拥有、已过保、内容可全清的设备。

配套阅读：越狱成功后，按 [SETUP.zh.md](SETUP.zh.md) 配置 SSH 通道和工具链。

[English](JAILBREAK.en.md)

## 目录

1. [开始之前：判定机型与固件](#1-开始之前判定机型与固件)
2. [方案选型](#2-方案选型)
3. [越狱前的准备](#3-越狱前的准备)
4. [SpiderCat 完整步骤](#4-spidercat-完整步骤)
5. [红线](#5-红线)
6. [踩坑实录](#6-踩坑实录)

## 1. 开始之前：判定机型与固件

越狱窗口按机型和固件一刀切，先拿到两个真值。

### 1.1 屏幕真值（最可靠）

Kindle 上进 设置 → 设备选项 → 设备信息，记下**型号**和**固件版本**。本机显示：Oasis 第十代 / 5.18.2。

### 1.2 U 盘真值（交叉核对）

USB 连电脑（设备会以 U 盘模式挂载），PowerShell 里：

```powershell
Get-Content H:\system\version.txt
# 本机输出: Kindle 5.18.2 (443455 025)
```

注意两个坑：

- **release_notes 会骗人**。`H:\system\release_notes\` 里可能只剩一份旧说明文件（本机是 2023-11 的 5.16.5 文案），它只记录某次历史更新的内容，不代表当前固件。真值看 `version.txt` 和屏幕。
- **Windows 资源管理器把 `system` 目录标成隐藏**。资源管理器看不到就用 PowerShell 或 Git Bash 的 `ls`，U 盘模式下 `system` 目录本身可读写。

### 1.3 序列号与型号

序列号第 4 到 6 位是 devcode，kindlemodding 的 models.json 用它查机型。本机序列号 G000WL******（已打码），devcode `0WL`，对应 `KindleOasis3WiFi8GB`，platform Zelda / board Stinger，2019 年发售，出厂 5.12.0，**该机型最后一版固件（last_firmware）就是 5.18.2**，产品线已冻结。

分辨率也能辅助确认：Oasis 3 是 1264x1680（Paperwhite 5 是 1236x1648，Scribe 是 1860x2480）。

### 1.4 固件窗口压力

因为 5.18.2 已是该产品线终点，这台机器没有「升上去窗口就没了」的压力。即便 Amazon 推一个小版本，SpiderCat（覆盖到 5.19.5）和 Nosebleed（到 5.18.6）也仍然覆盖。老机型（如停在 5.16.x 的 Paperwhite）则完全不同：升级可能永久关掉所有越狱窗口，那类机器要先做防自动更新（见第 3 节）。

## 2. 方案选型

先读官方向导 kindlemodding.org 的 Jailbreak Wizard，它会按你的机型和固件给出可用方案。下表是 KOA3 + 5.18.2 组合的实算结果（依据官方 jailbreaks.json，2026-10）：

| 方案 | KOA3 覆盖固件 | 5.18.2 可用 | 前置条件 | 注入方式 |
|---|---|---|---|---|
| **SpiderCat** | 5.16.3 – 5.19.5 | 可用 | 无（不需注册、不需广告） | 一个 azw3 侧载进 documents，书库里点开 |
| Nosebleed | 5.16.4 – 5.18.6 | 可用 | 无 | 两个文件放 U 盘根目录，自带浏览器开 kindlemodding.org/nosb |
| AdBreak | 5.18.1 – 5.18.5.0.1 | 可用 | 必须带广告（Special Offers）且已注册 | 替换 `system/.assets/` 里的广告 details.html，回插后点广告 |
| WinterBreak2 | 5.6.1.1 – 5.16.3（白名单含 5.16.5） | 不可用 | 无 | 浏览器开 penguins184.xyz/wb2 |
| WinterBreak | 5.18.0.2 及更低 | 不可用 | 需注册并进 Kindle Store | 基于 Mesquito 漏洞，5.18.1 起失效；国行商店 2023 年已关停 |

选择逻辑：

- **5.18.x 的首选是 SpiderCat**：条件最少（不要广告、不要注册、不要商店）、覆盖最宽（到 5.19.5）、注入动作最少（点开一本书）。本机即用此方案。
- 带广告的机器可以把 AdBreak 当备胎。反过来说，走 SpiderCat 就**不要付 19.99 美元去移除 Special Offers**：免广告的「假书封面当锁屏」路线和 AdBreak 互斥，留着广告无害。
- LanguageBreak、diunes、USBarm、KUAL+MRPI 这些老方案上限 5.16.2.1.1，对 5.18.2 全部无效。中文社区还在流传的旧教程（bookfere 那篇 KUAL/MRPI 流程）不要照抄。
- 越狱全部走 userstore（patchedUks.sqsh），不碰 rootfs。出错可用「恢复出厂」还原（见第 5 节），可逆，变砖概率低。

## 3. 越狱前的准备

1. **确认固件在窗口内**（第 1 节），并确认方案前置条件（SpiderCat 无前置）。
2. **别手动挡升级**（仅限 last_firmware 已到位的机型）：不往 U 盘根目录放任何 `update*.bin`，不点设置里的「更新您的 Kindle」。老机型需要防 OTA 的做法（灌满存储只留 50–90MB 等）见 kindlemodding.org 的 FAQ。
3. **备好回退方案**：把 Nosebleed 的文件包下好放在电脑上，SpiderCat 失败时再动，不现找。
4. **文件校验工具**：Git Bash 自带 `sha256sum`，或 PowerShell `Get-FileHash`。
5. **预期管理**：全程只做文件操作 + 一次点书，期间设备要开 Wi-Fi 且保持联网直到完成。失败的最坏结果通常是「没成功」，重来一次即可。

## 4. SpiderCat 完整步骤

以下为本机实录流程（Windows + Git Bash，U 盘挂载点 `H:`，按你的实际盘符调整）。

### 4.1 下载并校验 spidercat.azw3

从 kindlemodding.org 的向导进入 SpiderCat 页面下载 `spidercat.azw3`，然后校验：

```bash
sha256sum spidercat.azw3
# 本机 2026-10 取得的文件：
# F07E25C2003CAC4BFB381D70AB784C8B0CF996CD6A499A18116405B224046062  spidercat.azw3
# 484289 字节
```

上游没有单独公布校验和，上表哈希只对应 jb.sh v2.2.1 时期的那份文件；若上游已更新，以官方页面为准，核对到「来源是 kindlemodding.org 且经 HTTPS 下载」这一层即可。这个 azw3 会以 root 身份执行代码，不接受来路不明渠道的副本。

### 4.2 侧载进设备

1. USB 连接 Kindle，等它以 U 盘模式挂载。
2. 把 `spidercat.azw3` 拷进 `documents\` 目录。
3. 核对设备上文件的哈希与本地一致（本机做法，防止拷写损坏）：

   ```bash
   sha256sum H:/documents/spidercat.azw3
   ```

4. 安全弹出 U 盘。

### 4.3 点书执行（人在设备上的唯一操作）

1. 在 Kindle 上打开 Wi-Fi，**保持联网直到流程结束**。
2. 主页进书库，找到 **SpiderCat** 这本书，点开。
3. 预期现象（官方口径 + 本机一致）：
   - 开头几秒白页或只有封面，**继续等**；
   - 文字从屏幕顶部往下滚，滚到底出现 **Bang!**，脚本开始跑；
   - 期间可能弹出 **application error，属预期内，直接忽略**。
4. 看不到这本书时：主页下拉刷新图书馆，或重启一次设备再看。

### 4.4 确认越狱成功

重新插 USB，检查三个标志（本机全部命中）：

```bash
cat H:/documents/JAILBROKEN.txt
# You are jailbroken! (jb.sh v2.2.1)

cat H:/privesc_marker.txt
# jb.so constructor: uid=0 euid=0 pid=15544     <- root 代码确实执行过

ls -la H:/libkh/bin/fbink
# 约 1.38 MB，FBInk 1.25.0 已由 jb.sh 落地
```

`system/version.txt` 应该还是 5.18.2，固件没被动过。

### 4.5 重启并装包管理器组件

官方要求刚越狱完重启一次。重启后（保持 Wi-Fi 开启）：

1. 主页搜索框输入 `;kpm update` 回车。预期：屏幕顶部滚过几行字后回到主页。
2. 搜索框输入 `;kpm install koreader` 回车，预期同上；装完书库会出现 KOReader 图标。

本机备注：这两条搜索框命令当时没由人执行，KOReader 是后来用 scriptlet 通道以 `sh /var/local/kmc/sbin/kpm.sh install koreader` 单进程装的（见 [SETUP.zh.md](SETUP.zh.md) 第 4 节）。两条路径等价，搜索框是官方标准路径。**无论哪条，同一时间只允许一个 kpm 进程**，并发安装会写坏包（踩坑实录 6.5）。

### 4.6 此时你有了什么

- root 执行能力：SpiderCat 自带 sh_integration，`documents/` 里任何 `.sh` 会被索引成书，点开即以 root 执行（60 秒超时，详见 SETUP.zh.md 第 3 节的机制说明）。
- `/mnt/us/libkh/bin/fbink`：FBInk 1.25.0 全功能版（图像 + TrueType）。
- `/var/local/kmc/sbin/kpm.sh`：KPM 包管理器（不在 PATH 里）。
- 设备原有工具：busybox 1.34.1（含 telnetd）、eips、lua、iptables、curl。没有 dropbear/sshd/python/perl。

下一步全部在 [SETUP.zh.md](SETUP.zh.md)。

## 5. 红线

### 5.1 永远不写 rootfs

10 代及以后的 Kindle 有 secure boot，rootfs 刷坏**没有任何本地救砖手段**（官方的分区备份/还原只对 8 代及更早有效），KPM 官方也明令禁止。本项目全部运行时文件放 `/mnt/us`（userstore，可执行位有效）和 `/var/local`（可写、非 rootfs、重启不丢）。

### 5.2 防自动更新

- 越狱后 jb.sh 的系统补丁会拦截 OTA（上游文档口径，本机未单独验证拦截行为；本机 last_firmware 已到位，压力本来就小）。
- 自己遵守三条纪律：不点设置里的「更新您的 Kindle」；U 盘根目录不放 `update*.bin` 或 `update.bin.tmp.partial`；来路不明的 `.bin` 一律不装。
- 需要手动更新固件时（有意为之，且确认新固件仍有可用越狱方案），才放 Amazon 签名的 `.bin` 到根目录。

### 5.3 挂起类实验先确认人在场

裸 `echo mem > /sys/power/state` 在这台 5.18.2 上是单程票：RTC 闹钟唤不醒、电源键唤不醒，只能长按电源强制重启。实测记录见 `daemon/DESIGN.md`。任何挂起/休眠相关实验，先确认用户在场再动手。

### 5.4 恢复出厂（越狱的最后退路）

- **触发方法**：U 盘根目录放一个名为 `DO_FACTORY_RESTORE` 的空文件，重启设备即进入恢复出厂（KindleModding 文档口径）。恢复出厂会清掉越狱和全部内容。
- **强制重启**（卡死时的唯一手段）：长按电源键 20 秒以上。越狱打在 userstore 上，重启不丢，损失的只是运行态（telnetd、iptables 规则等），重来即可。
- 恢复出厂后想继续玩，把第 4 节重跑一遍即可。

## 6. 踩坑实录

以下是本项目前期探索时真实走死的路线，写在这里帮读者绕开。全部发生在越狱成功之后、配置 SSH 通道的阶段。

### 6.1 PC 侧代理 TUN 抢路由（症状：能连上但立刻被掐）

现象：`telnet 192.168.0.100 23` 能建立 TCP 但对端不发任何数据就复位；SSH 端口同样症状。

根因：PC 的 Clash TUN 虚拟网卡（接口名 Meta，198.18.0.1/30）把发往 Kindle 的流量接走了，回应 TCP 的是隧道接口，Kindle 从头到尾没被连过。判定方法：

```powershell
Find-NetRoute -RemoteIPAddress 192.168.1.189
# 看出接口：指向 "Meta"/TUN 就是抢了；指向物理网卡才对
```

解法（任选）：

```powershell
# 一次性主机路由（要管理员权限，只影响这一个 IP）
route add 192.168.1.189 mask 255.255.255.255 192.168.1.1
route delete 192.168.1.189   # 撤销
```

或在 Clash Verge 覆写配置里让 TUN 排除局域网段（改完要重载内核才生效）：

```yaml
tun:
  enable: true
  route-exclude-address:
    - 192.168.1.0/24
    - 10.0.0.0/8
    - 172.16.0.0/12
```

后续验证：PC 和 Kindle 在**同一网段**时 Clash TUN 不抢同网段流量。当时抢走是因为 PC 在有线网段、Kindle 在另一个无线网段。优先让两台设备同网段，多数代理配置不用动。

### 6.2 路由器有线无线隔离（症状：设备全绿但谁都不应答）

现象：设备侧全部正常：telnetd 在 `0.0.0.0:23` 监听、iptables 规则已插到链首、能 ping 通网关、PC 侧 ARP 能解析到它的 MAC。但 PC 的 SYN 有去无回，扫描也探不到端口。

根因：路由器对**有线口 ↔ 无线客户端**做了隔离（AP isolation / 客户端隔离）。设备默认防火墙策略是 `-P INPUT DROP`，跨隔离边界的包根本到不了它。这个隔离只存在于有线和无线之间，无线侧内部没有。

解法：让 PC 也连同一个 Wi-Fi（走无线侧），隔离消失。本机 2026-10-16 验证：PC 连上 Wi-Fi 后 SSH 直通。不想动路由器设置的话，这是成本最低的路。

取证顺序建议：先 `arp -a` 看设备 MAC 在不在（在 = 二层通），再对照设备侧日志确认监听和防火墙，最后才怀疑路由器隔离。

### 6.3 USB 切网卡（USB RNDIS）在 Windows 11 上走不通

现象：设备侧执行 `lipc-set-prop -i com.lab126.volumd useUsbForNetwork 1` + hal `usbUnconfigured`/`usbPlugOut` 后，`usb0` 正常起来，屏幕显示 USB NETWORK MODE；但 Windows 上既没有 U 盘也没有新网卡，只有一个打不开的 COM5 串口。

根因（本机取证 + 内核源码核对）：设备切出的是内核 legacy `g_ether` gadget，RNDIS 产品号 VID_0525:PID_A4A2。它的 RNDIS 控制接口类是 Class 02/SubClass 02，被 Windows 的 `usbser.inf` 抢注成串口；in-box 的 `rndiscmp.inf` 只认带 MS OS 1.0 描述符的设备，legacy gadget 不发这个描述符，所以**永远不会出现网卡**。COM5 也不是控制台（设备侧没有 ACM 功能），Code 10 打不开是必然。同症状 2016 年起有记录，当年的解法是自制签名驱动，Win11 上不建议再走。

解法评估后放弃：要在 Windows 出网卡，得在设备上用 configfs 自建 rndis 功能并伪造 MS OS 描述符，还要先解绑 Amazon 自己的 mtpgadget，且 KOA3 内核是否编了 `libcomposite`/`usb_f_rndis` 未验证。不值得拿设备试。

附带事实：`useUsbForNetwork` 是 volumd 的内存态属性，重启自动归零；Oasis 2/3 有 `usbUnconfigured` 引发内核 panic 的先例，设备当时没挂但主机侧枚举半死，重插线才恢复。

结论：这台机器插着 USB 就锁在 U 盘模式（`/mnt/us` 被摘走交给主机、Wi-Fi 挂起），USB tethered 开发在此机型上本来就不成立。老老实实走 Wi-Fi。

### 6.4 设备休眠冻结一切

现象：点完书、拔了线，几十秒后 PC 侧 ARP 还在但任何端口都不通。

根因：Kindle 休眠会冻结用户进程并关 Wi-Fi。`preventScreenSaver` 只挡屏保，不挡深睡；靠文件轮询的常驻 agent 在设备睡着后完全不跑。点书这个动作本身保证设备醒着，所以点书触发比后台轮询可靠。

解法：开发期用 scriptlet 打开 `lipc-set-prop -i com.lab126.powerd preventScreenSaver 1`（注意它只防屏保，配合周期性重新声明能撑住清醒时间）；正式方案是看板 daemon 的 ac 模式常驻 + 自己管理休眠策略（SETUP.zh.md 第 8 节）。

### 6.5 kpm 并发安装写坏包

现象：KOReader 下载到 10% 停住，安装失败。

根因：两个安装流程并发跑，两个 kpm 进程同时写同一个临时文件 `/mnt/us/kmc/kpm/packages/tmp/koreader_*.kpkg`，都读到截断的包。

解法与纪律：同一时间只跑一个 kpm；长任务必须 `setsid` 脱离（scriptlet 有 60 秒硬超时）且期间不拔线（拔线会摘走 `/mnt/us`，正在往那里写的过程直接断）。教训浓缩成两条：一次拔线周期打包一批命令；不要并发跑两个写同一文件的安装。

### 6.6 参数以设备实测为准，不凭记忆

前期凭记忆写的 FBInk 参数有一半是错的（`-r/--rot`、`-l/--light`、`-w A_DUST`、`-P --No-pep`、`--discard` 都不存在；真实语义是 `-r`=rpadded、`-w`=wait、`-P`=progressbar）。以设备上 `fbink --help` 和源码为准。另外 `fbink -e` 在这台机上段错误，禁用；取屏幕参数用 `eips -i`。
