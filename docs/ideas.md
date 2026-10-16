# Kindle Oasis 3 玩法调研（2024–2026 社区玩法扫描）

调研日期：2026-10-16。角色：玩法研究员，只调研，未碰设备、未写实现代码。

Star 数与更新时间均为 2026-10-16 通过 GitHub API 实查，未美化。

## 0. 调研范围与诚实声明

**搜了的渠道**：GitHub（gh API 全量检索 30+ 仓库并逐个读 README）、Reddit（经 WebSearch 间接命中 r/selfhosted、r/eink、r/kindlejailbreak、r/koreader 帖子）、MobileRead（经搜索摘要与项目 README 交叉引用，原帖未能直接打开——Jina Reader 对 mobileread.com 临时封锁）、B站（bili CLI 实搜 16+ 视频）、博客/XDA/HowToGeek/GeekWire（经搜索与 Jina 抓取）。

**没搜成的渠道**：
- X 站内搜索：无 cookies 凭据，未做。仅收录了 adtac gist 里附带的演示推文链接（该推文真实性由 gist 作者背书，未直接验证）。
- 小红书：无登录态，未搜。中文圈覆盖以 B站 + GitHub 中文项目为主。
- Exa 语义搜索：本机未配置，改用 WebSearch。

**可信度分级**（每条记录标注）：
- 【已核实】GitHub API 实查 + README 完整阅读 + 有实机照片/视频或多个独立来源交叉
- 【单一来源】出处真实存在，但只有作者自述，无第三方跟做验证
- 【无法核实】未找到实跑证据，或只有二手转述

**与项目 AGENTS.md 的冲突说明**：任务简报说「KOReader 已装」，但项目 AGENTS.md（2026-10-05/06 会话核实，10-16 更新）记录「KOReader 未装成（两次并发 kpm 写坏包，需重装）」，且 dropbear 是从残缺的 /mnt/us/koreader 目录里拿的。本报告以 AGENTS.md 为准：**所有 KOReader 类玩法的成本都含「先重装 KOReader」这一步（小时级）**。设备无 python/perl、有 lua/eips、FBInk 1.25（`fbink -e` 段错误禁用）、不写 rootfs（10 代 secure boot 无救砖手段）——可行性评估全部按这个基线。

---

## A. 看板 / 状态屏（与主人工作流最相关）

### A1. AI agent 用量推送看板（PC 渲染 → Kindle FBInk 上屏）
- **是什么**：在 PC/NAS 侧采集 Claude Code、Codex 等 agent 的使用数据，渲染成 Kindle 友好的灰度 PNG，Kindle 定时拉取或被推送后用 FBInk 刷屏。四个代表项目：
  - **alexishida/kindle-dashboard**（302★，更新 2026-07）：Electron 桌面应用，采集 Claude Code 和 OpenAI Codex 本地用量，渲出 PNG 供 Kindle 经 SSH+FBInk 拉取；带 Windows 托盘、诊断面板、多语言。设备端只跑 shell+FBInk。
  - **jackwuwei/kindle-dashboard**（3★，更新 2026-09）：中文项目，homelab 看板带 **Claude 订阅用量卡（5 小时窗口/每周限额）** + Glances + Home Assistant 温湿度；Pillow 预渲染，Kindle 端 dash.sh 每 5 分钟 curl 拉图。实机 PW2。
  - **t0saki/Kindle-Dashboard**（26★ + Server 14★，2026-08/09）：中文，KUAL 插件 + FBInk GC16 波形，独占模式关原生 Framework 防休眠，**本地时钟每分钟局部刷新**、对齐整分钟唤醒省电；配套服务端渲 1680×1264 十六级灰度抖动图。B站视频 1.66 万播放（BV1zmFXzcEhz）。
  - **jefftko/kindle-dashboard**（4★，更新 2026-09）：**就是 Oasis 3 / 1264×1680 / 固件 5.18.2 实测的同机型项目**。纯 POSIX shell + FBInk + OpenType CJK 字体直绘，Upstart 在 framework_ready 后启动，处理了屏保/休眠/USB 模式恢复、断网显示缓存、周期性全刷+非闪烁恢复波形防残影。
- **出处**：
  - https://github.com/alexishida/kindle-dashboard
  - https://github.com/jackwuwei/kindle-dashboard
  - https://github.com/t0saki/Kindle-Dashboard
  - https://github.com/jefftko/kindle-dashboard
- **成熟度**：【已核实】四个项目都有实机截图，t0saki 有 B站视频。
- **Oasis 3 可行性**：就是本项目已打通的路线（render.py → PNG → fbink GC16 全刷已验证全无线闭环）。增量工作只是卡片内容与生命周期健壮性。482MB 内存、无 python 都不受影响（python 在 PC 侧）。
- **接入成本**：小时级~天级（管线已通，加卡片/抄 jefftko 生命周期脚本）。

### A2. Home Assistant Lovelace 面板上 Kindle
- **是什么**：服务端定时对 HA 的 Lovelace 视图截图，转灰度，Kindle 端装 "Online Screensaver" 插件（MobileRead t=236104）轮询该图作为屏保/看板；sibbl 的实现做了图片比对，无变化时保持 ETag 不变让设备跳过下载刷新。
- **出处**：https://github.com/sibbl/hass-lovelace-kindle-screensaver （656★，更新 2026-10，A 组里星最多）；配套 https://github.com/sibbl/hass-kindle-screensaver （62★，自渲染 React 页）
- **成熟度**：【已核实】社区大量跟做（r/homeassistant 有多个帖子）。
- **Oasis 3 可行性**：设备侧只装 KUAL 插件（写 /mnt/us，不碰 rootfs），服务端在 PC 跑。**前提是主人得有（或愿意搭）Home Assistant**——为这一个玩法搭 HA 不值。
- **接入成本**：已有 HA：小时级；没有：天级（先搭 HA，不建议）。

### A3. TRMNL 生态借力（BYOD 把 Kindle 变 TRMNL 屏）
- **是什么**：TRMNL 是 2024–2025 走红的 e-ink 看板硬件+云服务（recipe 生态：日历/天气/HN/GitHub 贡献图等）。官方出了两条把旧 Kindle 变成 TRMNL 屏的路：`trmnl-kindle`（WinterBreak/AdBreak + 自家 zip）和 2026 年起推荐的 `trmnl-koreader`（KOReader 插件，Tools → TRMNL Display，Keep alive + 定时 dashboard 模式）。需要 BYOD license（付费）或 BYOD-S/BYOS（免费自托管渲染端）。
- **出处**：https://github.com/usetrmnl/trmnl-kindle （446★，2026-10 更新）；https://github.com/usetrmnl/trmnl-koreader （169★，2026-10 更新）
- **成熟度**：【已核实】官方维护，README 明确 beta、10/12 代实机测试。
- **Oasis 3 可行性**：KOReader 重装好后拷插件填 key 即可；Lua 插件只做 HTTP 拉图+显示，内存无压力。云端在境外，直连延迟需留意（可 BYOS 自建绕开）。
- **接入成本**：BYOD：小时级；BYOS 自建：天级。

### A4. 行情/状态状态屏（Bitcoin Status Display 模式）
- **是什么**：服务端 Node.js 聚合数据（BTC 价格、链上数据、闪电网络），Firefox 无头截图 → 灰度化 → cron 产出 display.png，Kindle 定时拉。架构与本项目管线同构。
- **出处**：https://github.com/dennisreimann/kindle-display （97★，更新 2026-09）
- **成熟度**：【已核实】作者长期实跑（d11n.net 有专文）。
- **Oasis 3 可行性**：高。换成主人要的行情源（A股/加密/汇率）是服务端改数据层的事。
- **接入成本**：小时级（已有渲染管线，只差数据源）。

### A5. 中文金融看板（中美港指数+天气）
- **是什么**：Flask+Docker 抓三大市场指数与天气，渲染适配墨水屏的看板图。
- **出处**：https://github.com/fedfwefsdfwe/Kindle-Finance-Terminal （0★，2026-04）
- **成熟度**：【单一来源】0 星、无跟做证据。
- **Oasis 3 可行性**：服务端渲染，技术上无障碍，但参考价值仅剩数据源清单。
- **接入成本**：自建等价物：天级。

### A6. 「老 Kindle 当看板」meta 教程（方案对比与电池实测）
- **是什么**：2025–2026 多篇系统总结：DIY 越狱 vs TRMNL vs HA 截图三路线；30 分钟刷新间隔下电池 2–4 周；e-ink 刷新瞬间 0.5–1W、待机≈0W。
- **出处**：
  - https://terminalbytes.com/kindle-dashboard-eink-display-2026 （2026-05，作者 PW7 实跑一年）
  - https://mxd.codes/articles/an-e-ink-homelab-dashboard-on-a-jailbroken-kindle （2026-08）
  - https://www.reddit.com/r/selfhosted/comments/1vq2gey/old_kindle_as_an_eink_homelab_dashboard
  - https://www.reddit.com/r/kindlejailbreak/comments/1oude8r/turned_my_old_kindle_into_a_live_desk_display
- **成熟度**：【已核实】多位作者独立实跑。
- **可行性**：结论与本项目现状一致（服务端渲染 + 低频刷新 + FBInk）。电池数字可作为刷新间隔设定依据。

---

## B. 时钟 / 天气 / 日历 / 相框

### B1. H5 浏览器时钟（原生系统路线，无需 KOReader）
- **是什么**：Kindle 自带实验浏览器打开一个 H5 页面（时钟/天气/农历/热搜），搜索框 `~ds` 关休眠常亮。代表：**1pone/clockindle**（353★，时钟/天气/相册/微博热搜，最后更新 2023-12）；**0111/Kindle_WeatherCN**（42★，2026-08 更新，中文台历，2025 版修了时间同步，支持自建）；知乎/CSDN 有大量跟做（zhuanlan.zhihu.com/p/616548246 等）。
- **出处**：https://github.com/1pone/clockindle ；https://github.com/0111/Kindle_WeatherCN
- **成熟度**：【已核实】中文圈多年跟做，B站多条视频。
- **Oasis 3 可行性**：技术上通，但两点不适合本机：`~ds` 常亮 + 浏览器常驻耗电大、长期静态页面有残影风险；原生浏览器渲染 1264×1680 适配一般。主人已有推送管线，此路线价值低。
- **接入成本**：小时级（书签即可），但不推荐长期挂机。

### B2. 天气站（服务端渲染 PNG 路线）
- **是什么**：经典玩法（2012 年 mpetroff 首创，至今仍被引用），服务端渲天气图，Kindle 低频拉取。代表仓库：**mpetroff/kindle-weather-display**（292★）、**matopeto/kindle-weather-dashboard**（273★）、**cathay4t/kindle-weather**（110★）、**x-magic/kindle-weather-stand-alone**（60★，免服务端 standalone，中文圈常用底子）、**mattzzw/kindle-weatherstation**（44★，无服务器 + 电池优化：按需唤醒 WiFi）、**terminalbytes/kindle-dashboard**（92★，配套 2025-02 博客，实跑一年+）。
- **出处**：https://github.com/mpetroff/kindle-weather-display 等上列仓库；https://terminalbytes.com/reviving-kindle-paperwhite-7th-gen/
- **成熟度**：【已核实】十年生态，实机无数。
- **Oasis 3 可行性**：天气卡只是 render.py 的一种卡片内容，一天内可加。mattzzw 的「每次刷新前才拉网、其余时间深睡」思路值得抄进本项目 daemon。
- **接入成本**：小时级（加一张天气卡）。

### B3. 日历（Outlook/PDF）
- **是什么**：
  - **ShaderFallback/KindleOutlookCalendarWeather**（90★，中文，三模式：Outlook 日历/RSS/时间）。**坑：要求给 Kindle 装 Python3.9**——与本项目「不写 rootfs、设备无 python」基线冲突，不采纳。
  - **Wsine/kindle-calendar**（45★）：生成 PDF 日历拷进 Kindle 手动看，零风险。
  - **MartinPham/kindle-calendar**（42★）：日历转换。
- **出处**：上列仓库。
- **成熟度**：【已核实】（ShaderFallback 有实机照片；star 数不高但中文圈有引用）。
- **Oasis 3 可行性**：日历需求建议并入本项目 A1 管线（服务端渲染日历卡），不装设备端 python。
- **接入成本**：日历卡：天级；PDF 路线：小时级。

### B4. 相框 / 屏保内容玩法
- **是什么**：
  - **aesuli/Kindle-Photo-Frame**（20★，2026-10 更新）：随机图片轮换相框。
  - **ZhxChen/daily-kindle-screensaver**（2★，2026-10）：中文，越狱 Kindle 天气+农历+节气+预报**锁屏壁纸自动更新系统**，Web 面板 + Docker。
  - **hishucheng/douban-kindle-screensaver**（0★）：豆瓣半年阅读记录自动生成屏保。
  - **KOReader customisablesleepscreen.koplugin**（283★，活跃）：睡眠屏显示阅读统计/随机书摘/自定义图，10 个预设、按时间表或夜间模式自动切换——休眠状态当「数据相框」用，几乎不耗电，防残影天然（每次全刷）。
- **出处**：上列仓库。
- **成熟度**：customisablesleepscreen【已核实】（社区主力插件）；相框小项目【单一来源】居多（README 有、跟做证据少）。
- **Oasis 3 可行性**：高。屏保路线是「设备大部分时间在睡觉」前提下的最优展示位，与看板路线互补。
- **接入成本**：KOReader 插件：小时级；自建屏保推送：复用本项目管线，天级。

---

## C. 终端 / 副屏 / VNC

### C1. kterm：Kindle 原生终端模拟器
- **是什么**：bfabiszewski/kterm（403★，持续维护）——Kindle 上的终端模拟器，带嵌入式虚拟键盘，KUAL 启动，跑 busybox shell、ssh 客户端。B站有专视频（91创客学堂「Kindle改造墨水屏Linux终端」，4806 播放，BV1Mi346XERK）。
- **出处**：https://github.com/bfabiszewski/kterm
- **成熟度**：【已核实】MobileRead 老牌工具，star 数在 Kindle 专用软件里属于头部。
- **Oasis 3 可行性**：装 /mnt/us 即可，不碰 rootfs。作为**输出屏**（跑一条长命令看日志尾巴、看 agent 输出）成立；Oasis 3 无实体键盘，虚拟键盘打字慢，作为**交互终端**体验一般。配合 `ssh` 到 PC 反向操作可行。
- **接入成本**：小时级（KUAL+kterm 安装包）。

### C2. JailbreakedKindleGPT：kterm 里跑 ChatGPT（纯 shell 客户端）
- **是什么**：Bourne shell + curl + grep/sed 手撕 JSON（无 python 无 jq），在 kterm 里跑一个对话式 ChatGPT 客户端。
- **出处**：https://github.com/ronibandini/JailbreakedKindleGPT （3★）
- **成熟度**：【单一来源】作者自述+截图，无第三方跟做。
- **Oasis 3 可行性**：思路对本机极简可行（busybox 有 wget/curl 需现场确认，lua 也能兜底解析），指向本机可信网关即可变成「桌面 agent 问答终端」。但显示体验是 80 列文本流，酷炫程度一般，且 Assistant 插件（D2）已覆盖该需求且体验更好。
- **接入成本**：小时级。

### C3. Kindle 当 PC 副屏（截屏推送式「显示器」）
- **是什么**：PC 端 `screencapture`/截图 → ImageMagick 转灰度 → netcat 推给 Kindle 上的 30 行监听程序 → `eips` 刷屏。adtac 的 gist 实测 **3.5 fps（PW3）**，附 X 演示视频。2025-07 XDA、2026 HowToGeek 都写过同类文章（用 USBNetwork SSH over USB）。
- **出处**：https://gist.github.com/adtac/eb639d3c707b55a28f0ee9a420aa7e0c （演示：https://x.com/adtac_/status/1820127470613622950 ）；https://www.xda-developers.com/turned-old-kindle-into-second-monitor-for-pc-so-you-dont-have-to ；https://www.howtogeek.com/turn-old-kindle-into-e-ink-portable-monitor
- **成熟度**：【已核实】gist + 两家媒体 + 演示视频。
- **Oasis 3 可行性**：300ppi 大屏+FBInk 局部刷新，帧率不会明显好于 3.5fps，灰度+残影决定它**当不了真副屏，当「慢速信息屏」（日志尾、任务状态、番茄钟）成立**。Oasis 3 的 micro-USB 走 USBNetwork（gadget 模式）可有线推流。
- **接入成本**：天级（写监听+推流脚本，或直接复用本项目 ssh 推送）。

### C4. VNC 投屏
- **是什么**：**zanjie1999/kindle-vnc**（13★，中文 KUAL 插件，集成 VNC 服务端+客户端，修了反色、可旋转，依赖 kterm；配套 droidVNC-NG 可做安卓无 root 投屏）；**niutech/kindle-vnc**（15★，纯 HTML 方案）。作者在 README 里顺带怒斥了闲鱼「越狱收费/刷安卓」奸商。
- **出处**：https://github.com/zanjie1999/kindle-vnc ；https://github.com/niutech/kindle-vnc
- **成熟度**：zanjie1999【已核实出处】（中文圈有使用记录）；体验普遍评价为慢、分辨率适配麻烦。
- **Oasis 3 可行性**：技术上通但价值低——本项目已有 ssh 管道，VNC 属于「炫一下」玩法。
- **接入成本**：天级。

---

## D. KOReader 系玩法（重装后解锁）

> 前提：项目 AGENTS.md 记录 KOReader 需重装（kpm 并发写坏包）。重装本身小时级，注意单进程执行 kpm。以下官方插件均在 koreader/koreader `plugins/` 目录实查存在（2026-10-16 API 拉取）。

### D1. Assistant：KOReader 内置级 AI 插件（重点推荐）
- **是什么**：omer-faruq/assistant.koplugin（639★，2026-10-16 当天仍在更新）：阅读时划词调 AI（Claude/GPT/Gemini/DeepSeek/**Ollama 等一切 OpenAI 兼容端点**），问答/翻译/摘要/解释，不离开书页。增强 fork：zivshek 版加 Recap、X-Ray、基于高亮的总结；shipslow fork 加 web search。
- **出处**：https://github.com/omer-faruq/assistant.koplugin
- **成熟度**：【已核实】KOReader 生态 AI 插件的事实标准，社区活跃。
- **Oasis 3 可行性**：纯 Lua、无 python 依赖；模型请求走网络，端上只做 UI，482MB 内存无压力。**base_url 指向本机可信网关（magpie）即得「零 API 成本的阅读 AI」**。
- **接入成本**：小时级（装插件+填网关地址）。

### D2. appstore.koplugin：KOReader 应用商店
- **是什么**：617★。在设备上发现/安装/更新社区插件和 user patch（扫 GitHub topic `koreader-plugin`），装 D1、D6、B4 等插件不用连线。
- **出处**：https://github.com/omer-faruq/appstore.koplugin
- **成熟度**：【已核实】。
- **可行性/成本**：可行性无障碍；小时级。

### D3. NewsDownloader（官方内置）：每日 AI 热榜的零渲染方案
- **是什么**：官方插件（newsdownloader.koplugin），定时抓 RSS/Atom 源，排版生成电子书，开屏即读。配合自建 Miniflux（miniflux.koplugin，113★）、Readeck（133★）、wallabag（官方）可扩展成稍后读管线。
- **出处**：koreader/koreader plugins 目录实查；https://github.com/AlgusDark/miniflux.koplugin
- **成熟度**：【已核实】官方插件，多年主力功能。
- **Oasis 3 可行性**：完全无 python、无渲染依赖。「每日 AI 热榜」可以不经过本项目渲染管线直接达成：把 HN/AI 新闻源/官方博客 RSS 配进去，早晨抓取，翻开就看。缺点：不是「看板」，是要翻页读的电子书形态。
- **接入成本**：小时级。

### D4. terminal.koplugin + SSH.koplugin（官方）：KOReader 里开 shell 和 SSH
- **是什么**：官方插件，KOReader 内直接开本地 shell；SSH 插件起 SSH 服务端（本项目已在用的 dropbear 即出自 KOReader）。
- **成熟度**：【已核实】官方源码在库。
- **Oasis 3 可行性**：与本项目现有 dropbear 通道重叠；价值在于 KOReader 重启后通道自动恢复，不依赖手动起 dropbear。
- **接入成本**：小时级。

### D5. autostandby + batterystat（官方）：电池治理
- **是什么**：autostandby.koplugin 让设备在 KOReader 里真正进入原生 standby 深睡；batterystat/systemstat 记录耗电。背景：koreader issue #13176（2025-01）记录了 standby 期间「unscheduled wakeup」导致 1%/小时 的漏电问题与排查。
- **出处**：koreader/koreader plugins 目录；https://github.com/koreader/koreader/issues/13176
- **成熟度**：【已核实】。
- **Oasis 3 可行性**：看板常驻场景与「深睡省电」天然冲突，解法是 t0saki/jackwuwei 式「对齐刷新时刻唤醒」，插件本身在阅读场景用。小时级。

### D6. Kodashboard：阅读数据 Web 面板
- **是什么**：100★。KOReader 插件，起本地 web server，手机/电脑浏览器看藏书、进度、统计、笔记高亮。作者明确警告：网络是 Kindle 最大耗电项，**按需短开，不要常驻**。
- **出处**：https://github.com/Yuchen971/Kodashboard
- **成熟度**：【已核实】。
- **可行性**：高；注意作者的使用建议。小时级。

### D7. koreader-tailscale：Tailscale 组网进 Kindle
- **是什么**：228★。KOReader 插件，设备加入 tailnet，OPDS/进度同步走 tailnet 绕开内网限制。下载约 57MB，需 ARM 架构匹配。
- **出处**：https://github.com/victoria-riley-barnett/koreader-tailscale
- **成熟度**：【已核实】。
- **Oasis 3 可行性**：能跑，但本机场景（桌面+同网段）用不上；除非要「出门也能推卡」。小时级，优先级低。

### D8. 阅读流增强插件群
- **是什么**：bookends.koplugin（503★，文字叠加/token 图标）、anki.koplugin（236★，查词自动生成 Anki 卡）、highlightsync.koplugin（236★，WebDAV/Dropbox 同步高亮笔记）、foot-cream（106★，单位换算）、readwisereader（99★，Readwise Reader）、customisablesleepscreen（283★，见 B4）。
- **出处**：各仓库（GitHub 检索实查）。
- **成熟度**：【已核实】均为活跃社区插件。
- **Oasis 3 可行性**：全部是 Lua 插件，Oasis 3 无障碍。highlightsync 对「读书笔记进 AI 工作流」有想象空间（高亮同步到 WebDAV → agent 消费）。均为小时级。

---

## E. 翻页键 / 外设

### E1. Amazon 官方翻页遥控 Kindle Click（2026-10 新品）
- **是什么**：Amazon 官方 $34.99 蓝牙翻页遥控器，2026 年 10 月与新款 Kindle 一同发布。
- **出处**：https://www.geekwire.com/2026/kindle-gets-a-clicker-amazon-unveils-35-page-turning-remote-and-refreshes-its-e-reader-lineup
- **成熟度**：【单一来源】（仅 GeekWire 报道见到，未查 Amazon 官网与国内发售情况）。
- **Oasis 3 可行性**：若为蓝牙 HID 且 Oasis 3 固件支持，原生可能直接配对；走 KOReader 的 externalkeyboard/kindlebtcontroller 则更稳。对看板玩法可当「无线切页器」。
- **接入成本**：小时级（+硬件钱）。

### E2. kindlebtcontroller.koplugin：蓝牙手柄/翻页器映射（重点推荐）
- **是什么**：105★，中文文档。KOReader 插件：蓝牙手柄/遥控器→翻页、亮度、色温、章节、书签、强制全刷、KOSync 等 20+ 动作，可自定义键位、自动重连、内置键码测试器。README 列了多个 Kindle 机型验证通过。
- **出处**：https://github.com/finlater/kindlebtcontroller.koplugin ；r/koreader 讨论 https://www.reddit.com/r/koreader/comments/1t1h64j/bluetooth_page_turner_for_koreaderkindle ；官方原生支持仍是 open issue：koreader/koreader#13240（2025-02）
- **成熟度**：【已核实】（Reddit 帖 + 仓库截图 + 多机型验证）。
- **Oasis 3 可行性**：淘宝任意蓝牙翻页器/媒体遥控（HID 键盘类）即可。**对看板的衍生玩法：把翻页键映射成「看板切页/强制全刷/唤醒 WiFi」，给桌面看板加物理交互**。
- **接入成本**：小时级（KOReader 重装后装插件+配对）。

### E3. WiFi/自制翻页器
- **是什么**：MobileRead 有 WiFi 翻页器方案（t=367471）；liquidguru gist 记录了 PW6（12 代）蓝牙遥控+KOReader 全自动翻页配置。
- **出处**：https://www.mobileread.com/forums/showthread.php?t=367471 ；https://gist.github.com/liquidguru/1e9c77f9389cdf23f94d2a94b220c90a
- **成熟度**：【已核实出处】（原帖经二手引用确认存在，细节未逐条复现）。
- **可行性**：DIY 路线成本高于 E2，仅作参考。天级。

---

## F. 电池与屏幕保护（看板常驻的前提）

### F1. 电池技巧
- **是什么**：社区共识三条——①飞行模式/关 WiFi 是最大头（BGR 2026-05 引 Reddit：Oasis 从 2 天到 1 周）；②KOReader autostandby 保证真·深睡（参见 D5 的漏电 issue）；③看板场景用「低频刷新+按需唤醒 WiFi」：terminalbytes 实测 30 分钟刷新间隔撑 2–4 周；MP 有社区 AirPlane Mode 插件（t=368020）。
- **出处**：https://www.bgr.com/2154384/changing-this-kindle-setting-will-instantly-boost-battery-life ；https://terminalbytes.com/kindle-dashboard-eink-display-2026 ；https://www.mobileread.com/forums/showthread.php?t=368020 ；https://github.com/koreader/koreader/issues/13176
- **成熟度**：【已核实】多来源交叉。
- **Oasis 3 落地建议**：看板 5–30 分钟一刷 + 刷新前才拉网 + 平时保持飞行模式由脚本按需解开（t0saki 的「对齐整分钟唤醒」思路）。

### F2. 残影 / 烧屏防护
- **是什么**：e-ink 真正永久烧屏罕见，常见是残影（ghosting），全刷即清。**关键发现：MobileRead 2025-03 帖子报告固件 5.18.1 残影变差**——与本机 5.18.2 同代固件，直接相关，设计时要把「周期性全刷」当一等公民。iFixit 对 12 代 Paperwhite 的建议同样是开 Page Refresh。jefftko 项目的做法：周期性 GC16 全刷 + 非闪烁恢复波形交替，平衡清晰度/残影/打扰。
- **出处**：https://www.mobileread.com/forums/showthread.php?t=367155 ；https://www.ifixit.com/Troubleshooting/Kindle_Paperwhite_12th_Gen/Screen+Ghosting/625939 ；https://github.com/jefftko/kindle-dashboard
- **成熟度**：【已核实】多来源。
- **Oasis 3 落地建议**：本机推送频率低（分钟~小时级），每 N 次局部刷插一次 GC16 全刷；夜间不刷新时段让屏幕进屏保（屏保本身全刷，天然清残影）。

---

## G. 冷门但有意思

### G1. 离线水墨养鱼 boring-pond
- **是什么**：中文项目，老 Kindle 上跑的离线水墨电子养鱼应用。https://github.com/hankzheng88-alt/boring-pond （0★，2026-08）
- **成熟度**：【单一来源】。
- **可行性**：若为静态帧轮换则本机管线可复刻（渲染 N 帧+定时推）；有意思但优先级低。天级。

### G2. 屏保变语言学习工具 Little-Langtale
- **是什么**：7★，把 Kindle 屏保变成语言学习卡（生词/例句屏保序列）。https://github.com/64bits/Little-Langtale
- **成熟度**：【单一来源】（有 README 与思路，跟做证据少）。
- **可行性**：思路可用本项目管线复刻（交易术语卡/单词卡推到屏保位）。天级。

### G3. kindle-glance：KOReader 阅读 + 看板 A/B 启动
- **是什么**：中文，0★，自托管看板与 KOReader 阅读双模式启动管理。https://github.com/jijuwen/kindle-glance
- **成熟度**：【单一来源】。
- **可行性**：与本项目 autostart/hooks.d 设计同构，可参考其模式切换交互。天级。

### G4. Kindle 微信读书/番茄（B站 3–4 万播放教程）
- **是什么**：B站 2026 年多条高播放视频（Kindle精选君 3.96 万、木易知安 3.17 万）宣称越狱后可装微信读书/番茄/AI 问答插件。
- **成熟度**：【无法核实】未找到对应开源仓库或可复核的方案细节（疑似闭源脚本/收费服务，另有闲鱼收费乱象被 zanjie1999/kindle-vnc 作者点名）。不纳入推荐。

---

## H. 排除项（查过、不可靠或不适用）

- **DOOM/游戏上 Kindle**：GitHub 检索 "doom kindle"/"eink doom" 无 2024–2026 有效项目，旧闻不可靠，排除。
- **Kindle 刷安卓**：无可靠开源方案，中文圈已有收费诈骗案例（见 C4 出处），排除。
- **e-ink 电子徽章（badge）**：Kindle 上无既有项目（TRMNL/Inky 等专用硬件才有生态）；若要做属于从零自研，标注为「无出处概念」。
- **luutuankiet/kindle-mcp**（0★，"MCP bridge for Kindle PW3"）与多个 0★ send-to-kindle MCP：仅 README，无实跑证据，【无法核实】，不推荐；MCP 方向看 I2。
- **ShaderFallback 日历**：需设备端 Python3.9，违反本项目不写 rootfs/无 python 基线，技术排除。
- **1pone/clockindle 等浏览器常亮路线**：可行但不推荐（耗电+残影+与已有管线重复），见 B1。

**MCP 方向的综合判断**（对应任务里「MCP 外设」）：现存最接近的实例是 codecube/kindle-mcp-dashboard（1★，2026-10 更新，Paperwhite 1 实测跑通：MCP 客户端通过 tools 定义屏幕区域/组件并推状态，Kindle 只是渲染结果显示端）【单一来源但架构文档完整】。它的架构判断与本项目一致——**API key 和集成放服务端，Kindle 只是哑显示终端**。对本项目而言，给 render.py/push 管线包一层 MCP server（`push_card`、`set_dashboard` 两个 tool）就是「Claude 直接把卡片推上墨水屏」，无现成轮子，属自研天级工作，但方向已被验证可行。

---

## Top 3 推荐置顶

评分逻辑：酷炫程度 × 可行性 × 与主人工作流契合（herdr 多 agent 指挥、已规划的看板/交易卡/热榜）。

### 🥇 1. Agent 看板增强版：herdr 四 agent 状态卡 + 生命周期加固
**为什么第一**：契合度拉满（项目主线就是它），且四个现成蓝本把可行性风险压到最低——尤其 jefftko/kindle-dashboard 是**同机型同固件**的实跑项目，把最难的「休眠/屏保/USB 模式后恢复显示」直接抄答案；jackwuwei 的 Claude 用量卡（5h 窗口/周限额）和 alexishida 的 Codex 用量采集证明「agent 用量数据上墨水屏」已有人跑通。酷炫与实用兼具：桌面上眼睛一扫就知道四个 agent 谁在跑、谁限额了。
**如果要做，第一步**：读 jefftko/kindle-dashboard 的 README「lifecycle」部分，把它的「outOfScreenSaver 恢复重绘 + 断网缓存 + 周期性全刷波形」翻译成 `/mnt/us/qoder/autostart/hooks.d/` 下的看板 hook（autostart 骨架已部署好）；同时用 render.py 出第一张 `herdr 状态卡`（四行：agent 名/最近输出摘要/状态点），ssh 管道推送验证。这一步完成后天级工作量就是数据采集（抄 alexishida 的本地日志解析思路）。

### 🥈 2. KOReader 重装 + Assistant 插件接本机网关
**为什么第二**：成本几乎最低、体验差异最大的玩法。639★ 当天仍在更新的 omer-faruq/assistant.koplugin，OpenAI 兼容端点直接填本机可信网关，阅读时划词问答/翻译/摘要零 token 成本；appstore 插件再把整个社区插件生态（阅读统计屏保、高亮同步 WebDAV、Anki 制卡）解锁。对重度 AI 用户，「手边这台 7 寸墨水屏变成 AI 阅读伴侣」是日常渗透率最高的酷炫。
**如果要做，第一步**：单进程重跑 kpm 装 KOReader（AGENTS.md 记录的失败原因是两次并发写坏包，避免并发即可）；装好后第一件事验证 dropbear 通道还在，然后 appstore 或手动拷 assistant.koplugin，settings 里 base_url 指向网关、选一个便宜模型，划词试一轮中英翻译。

### 🥉 3. 每日 AI 热榜：NewsDownloader 零渲染路线（看板卡的补充）
**为什么第三**：已规划需求里成本最低的达成路径。官方 newsdownloader.koplugin 定时抓 RSS 生成电子书，完全不碰渲染管线、无 python、开机即读；与 Top1 的「看板卡」形成互补——看板管状态，热榜管阅读。若想要「图表化热榜」，再用已打通的 render.py 管线出一张热榜卡（天级），两者不冲突。
**如果要做，第一步**：收集 8–10 个 AI 资讯 RSS 源（Hacker News、各大 AI 官方博客、机器之心/量子位等中文源），KOReader 装好后配 NewsDownloader 的源列表 + 抓取周期（如每日 08:00），手动触发一次验证中文排版，再看是否需要自定义 CSS/字体调排版。

**落选但值得关注**：TRMNL BYOD/S（A3）——若想白嫖现成 recipe 生态（GitHub 贡献图、日历、HN）可小时级接入 trmnl-koreader 插件；但主人已有自建渲染管线，长期价值被 Top1 覆盖。蓝牙翻页器+kindlebtcontroller（E2）建议作为 Top1 的配件动作顺手做掉（翻页键=看板切页），不单列。

---

## 附：本次未覆盖与后续建议

- X 站内与小红书中文圈未搜（无凭据），如需补齐需先配置 twitter cookies / 小红书登录态再跑一轮。
- MobileRead 原帖（Online Screensaver t=236104、WiFi 翻页器 t=367471、5.18.1 残影 t=367155）只经二手引用确认存在，落地某项玩法前建议开浏览器确认帖子内最新回帖（尤其固件兼容性）。
- Amazon Kindle Click 国行发售情况未查。
