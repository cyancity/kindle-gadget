# kindle-gadget：把越狱 Kindle 变成 agent 推送的墨水屏看板

> **适用范围**：本项目全部工具链在一台设备上实测通过：Kindle Oasis 3（第 10 代，2019，国行 8GB Wi-Fi，序列号 G000WL******）+ 固件 5.18.2 + 越狱方案 SpiderCat（jb.sh v2.2.1）。其他机型或固件仅作参考，命令、路径、固件行为都可能不同。
>
> **安全声明**：越狱是非官方修改，有变砖和失去保修的风险，请自担。本教程面向你自己拥有、已过保、数据可全清的设备。全部操作不写 rootfs（见 [JAILBREAK.zh.md](JAILBREAK.zh.md) 红线一节）。

[English](README.en.md)

## 这是什么

一台越狱 Kindle Oasis 3，变成桌面上的一块墨水屏看板。herdr 里任意 agent（claude / codex / grok / omp）产出一段 HTML 或一张 PNG，一条命令推上屏幕：

```bash
python push.py cards/hello.html
```

约 2 秒后内容出现在 Kindle 屏幕上（GC16 全刷，黑闪一次）。小改动可用 `--partial` 局刷，无黑闪。看板 daemon 常驻时，推送只写文件，下一轮（默认 60 秒内）自动刷出。

效果：7 英寸 300ppi 墨水屏，1264x1680，16 阶灰度 Floyd–Steinberg 抖动，中文排版在 PC 侧渲染所以无字体问题。插电常驻模式下设备不休眠、每分钟检查新图。全链路走 Wi-Fi（SSH），不插线。

## 架构

```
        PC（Windows / Git Bash）                      Kindle Oasis 3（已越狱，root）
+-------------------------------+   SSH :2222    +-----------------------------------+
| agent (herdr / claude / ...)  |                | dropbear（KOReader 自带，仅密钥）  |
|   |  HTML / PNG               |                |   |                               |
|   v                           |  cat | ssh     |   v                               |
| render.py                     |  ----------->  | /mnt/us/qoder/card.png            |
|   Chrome headless 截图        |  (无 sftp/scp， |   |                               |
|   Pillow 16 阶灰度抖动        |   管道传文件)   |   v                               |
+-------------------------------+                | fbink -W GC16 -f -g file=...      |
                                                 |   |                               |
|  daemon 控制面（PC 侧）        |                |   v  电子墨水帧缓冲               |
|  python daemon/kd.py push ...  |  ----------->  | 1264x1680, 8bpp 灰度             |
|  （tmp+mv 原子写 current.png） |                | /mnt/us/qoder/daemon/dashboard.sh |
+-------------------------------+                |   60s 轮询刷屏，常驻              |
                                                 +-----------------------------------+
                                                        ^
                                                        | 开机自启
                                                 /etc/upstart/kmc.conf (SpiderCat)
                                                        -> /mnt/us/emergency.sh
                                                        -> /mnt/us/qoder/autostart/autostart.sh
                                                           (telnetd + dropbear + iptables + hooks.d)
```

四层职责：

| 层 | 位置 | 作用 |
|---|---|---|
| 渲染 | PC 侧 `render.py` | HTML 卡片 → Chrome headless 截图 → 16 阶灰度抖动 PNG。中文、复杂排版都在 PC 解决，设备保持愚蠢 |
| 推送 | PC 侧 `push.py` | 渲染 + `cat \| ssh` 管道传输 + FBInk 刷屏，一条命令 |
| 看板 | 设备侧 `daemon/device/dashboard.sh` | busybox ash 常驻循环，60 秒一轮：GL16 局部刷、每 6 轮 GC16 全刷清残影；PC 用 `daemon/kd.py` 控制和原子推送 |
| 自启 | 设备侧 `autostart/` | 走 SpiderCat 官方 boot 钩子 `/mnt/us/emergency.sh`，开机自动恢复 telnetd / dropbear / iptables，零 rootfs 写入 |
| 工作台 | PC 侧 `studio/` | 本地网页工作台：编辑卡片、真实渲染预览、圈注→本地 Agent 改稿、版本管理、系统托盘（见 [../STUDIO.md](../STUDIO.md)） |

## 快速开始

前提：一台 Kindle Oasis 3（其他 2019 年后的 Kindle 型号流程类似但未验证）、一台 Windows PC（Git Bash + Python 3.10+ + Pillow + Chrome 或 Edge）、设备和 PC 连同一个 Wi-Fi。

1. **越狱**：判定机型与固件，按 [JAILBREAK.zh.md](JAILBREAK.zh.md) 用 SpiderCat 越狱，拿到 root。
2. **配置通道与工具链**：按 [SETUP.zh.md](SETUP.zh.md) 逐步打通 SSH、装 KOReader/dropbear、验证 FBInk 渲染链。每一步都有验证命令和预期输出。
3. **推第一张卡**：

   ```bash
   python push.py cards/hello.html          # 全刷（黑闪一次）
   python push.py cards/hello.html --partial # 局刷（无黑闪，适合小改）
   ```

4. **常驻看板**：

   ```bash
   python daemon/kd.py start                # 部署并启动（幂等）
   python daemon/kd.py push out/xxx.png     # 原子推送，下一轮刷出
   python daemon/kd.py status               # 进程/配置/电量/日志
   ```

5. **开机自启**（可选，重启后通道自动恢复）：

   ```bash
   cd autostart && ./deploy.sh              # 部署 emergency.sh + autostart.sh
   ./deploy.sh --status                     # 查看监听端口 / iptables / 日志
   ```

6. **网页工作台 Studio**（可选，本机 127.0.0.1:8762）：编辑卡片 HTML、真实渲染预览（带 Oasis 设备壳、横竖屏）、圈注改稿、卡片版本管理、右下角托盘一键切换 Kindle 正常/看板模式。托盘需 `pip install pystray`：

   ```bash
   python studio/tray.py        # 托盘常驻；或 python studio/server.py 只起本地服务
   ```

7. **用量卡模板**：`python usage_card.py -o cards/usage.html` 从 ccusage 取本机 AI CLI 用量渲染成卡（无数据自动落 DEMO 样例），再 `python push.py cards/usage.html --orientation landscape` 上屏。

给 agent 的最小集成：任何能产 HTML/PNG 的 agent，跑一条 `python push.py <file>` 或 `python daemon/kd.py push <png>` 即完成上屏，细节见 `push.md`。

## 仓库结构

```
kindle-gadget/
+-- README.zh.md / README.en.md    本文件
+-- JAILBREAK.zh.md / .en.md       越狱教程（机型判定、方案选型、SpiderCat 步骤、红线、踩坑实录）
+-- SETUP.zh.md / .en.md           越狱后全套配置（SSH、KOReader、渲染链、daemon、自启）
+-- INDEX.md                       文档导航与未验证清单
+-- render.py                      HTML -> Chrome headless 截图 -> 16 阶灰度 PNG
+-- push.py / push.md              一条命令推送上屏；push.md 是给 agent 的调用说明
+-- telnet_run.py                  极简 telnet 客户端（备用 root 通道）
+-- rpc.py / tk.py                 早期文件 RPC / telnet 实验，留档
+-- cards/                         卡片 HTML 源（1264x1680）
+-- out/                           渲染产物
+-- daemon/                        看板 daemon：kd.py（PC 控制）+ device/（设备侧脚本）+ DESIGN.md
+-- autostart/                     开机自启：autostart.sh + emergency.sh + deploy.sh + DESIGN.md
+-- usage_card.py                  ccusage 用量卡模板（AI CLI 用量 -> 墨水屏卡片）
+-- screenshot.py                  从 /dev/fb0 抓屏幕（竖屏/横屏）
+-- scriptlets/ cmds/              bring-up 期间用过的设备侧 scriptlet 和命令批，留档参考
+-- vendor/                        早期探测遗留的 hotfix bin（本流程用不到，不入库，见 vendor/README.md）
+-- studio/                        网页工作台：server.py + index.html + tray.py + vendor/（CodeMirror、Inter 字体）
+-- docs/                          调研、设计文档与开源教程（docs/opensource/）
```

## 实测状态（2026-10-16/17）

已验证：

- SpiderCat 越狱（jb.sh v2.2.1），回执 `documents/JAILBROKEN.txt`，uid=0
- scriptlet 通道：`documents/*.sh` 点书即以 root 执行（SpiderCat 自带 sh_integration）
- 渲染链：render.py -> ssh 管道 -> FBInk GC16 全刷上屏，无线全闭环
- dropbear SSH（仅密钥，端口 2222），KOReader 经 kpm 单进程安装
- 看板 daemon ac 模式：60 秒轮询、GL16 局刷、每 6 轮 GC16 全刷、原子推送
- 开机自启已部署：语法检查、幂等冒烟通过；真实重启触发链已验证（2026-10-17 重启实测：telnetd/dropbear/iptables 自动恢复，hooks.d 自动拉起看板 daemon）

未验证 / 已知不可用：

- battery 模式（suspend + RTC 唤醒）实测失败，勿用，详见 `daemon/DESIGN.md`
- 其他机型、其他固件：全部未验证
- 完整清单见 [INDEX.md](INDEX.md)

## 相关文档

| 文档 | 内容 |
|---|---|
| [JAILBREAK.zh.md](JAILBREAK.zh.md) | 越狱：机型判定、方案选型表、SpiderCat 全步骤、红线、踩坑实录 |
| [SETUP.zh.md](SETUP.zh.md) | 配置：SSH/telnet 通道、KOReader、FBInk、daemon、autostart，每步含验证 |
| [INDEX.md](INDEX.md) | 导航 + 未完成清单（哪些命令没在别的机型/固件上验证过） |
| [../ideas.md](../ideas.md) | 社区玩法调研（看板、KOReader 插件、外设，含可信度分级） |
| [../STUDIO.md](../STUDIO.md) | 网页工作台（Studio）的设计契约与踩坑实录 |
