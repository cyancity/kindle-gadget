# kindle-studio：Kindle 推送工作台

网页工作台（Studio）的设计契约、决策与踩坑实录。状态：可用（编辑器/真实渲染预览/推送/圈注改稿/版本管理/托盘均已真机验证）。

## 需求

本地网页工作台：编辑卡片 HTML → 实时预览上屏效果（零偏差：服务端跑 render.py 出 PNG）→ 一键推送 Kindle。第一期含 ccusage 用量卡模板；第二期加圈注→LLM 改版式（magpie 网关）；开源文档整理为独立交付。

## 契约 v2：横竖屏（2026-10-16 晚）

- 方向枚举：`portrait`（1264×1680，默认）/ `landscape`（1680×1264）
- daemon 内容池：`/mnt/us/qoder/daemon/current.png` + `/mnt/us/qoder/daemon/meta`（**行格式** `key=value`，已实装：`orientation=portrait|landscape`、`force_full=1`（消费后自动清 0）、可选 `waveform=<GL16 等>`；不是 JSON）
- push 路径（push.py 与 studio /api/push）：渲染对应尺寸 → 写 current.png（tmp+mv 原子）→ 写 meta → 立即本地 fbink 画一次（landscape 需先切 fb 旋转，命令由设备 lane 定死后写入 push 脚本）→ daemon 下一轮按 meta 方向重画同一张图，实现持久
- studio UI：方向切换控件（竖屏/横屏），渲染与推送带方向；预览尺寸自适应
- 设备侧（leader 负责）：fb 旋转的切换/恢复命令、daemon 按 meta 方向画、帧缓冲调试文本清除、防休眠保活回收（电源键恢复）

## 契约（所有 lane 遵守）

- studio 核心：`studio/server.py`（stdlib http.server，只绑 127.0.0.1，端口 8762）+ `studio/index.html`（零前端依赖）
- server API：
  - `GET /` → index.html
  - `POST /api/render` body `{html}` → PNG 字节（调 render.py 同逻辑）
  - `POST /api/push` body `{html}` → 渲染+推送+FBInk，返回 `{ok, log}`
  - `GET /api/cards` → `[{name}]`（cards/ 目录）
  - `GET /api/card?name=` → `{html}`
  - `GET /api/usage` → `{ok, html}` 用量卡（usage_card.py 生成）
- usage 卡：`usage_card.py`，CLI `python usage_card.py -o cards/usage.html`；数据源 ccusage JSON；无 ccusage/无数据时内嵌 sample 数据兜底（卡面标注 DEMO）
- 卡片 HTML 约束：1264×1680 固定、无 flex gap/sticky/动画、字号 ≥30px、系统字体
- 设备约束、SSH 命令、坑：见项目 AGENTS.md
- 推送目标路径默认 `/mnt/us/qoder/card.png`（push.py 默认，勿改）

## usage-card 考证（usage-card lane，2026-10-16）

ccusage 版本 20.0.34（npx 实测），均已验证：

- 子命令：`daily` / `weekly` / `monthly` / `session` / `blocks`（通用聚合，已覆盖全部检测到的 agent），另每个 CLI 一个专属子命令，help 共列出 18 个：claude、codex、opencode、amp、droid、codebuff、hermes、pi、goose、kilo、copilot、gemini、antigravity、kimi、qwen、openclaw、grok、zcode
- 一次加载出三份报表：`daily --json --by-agent --sections daily,weekly,monthly --since <YYYYMMDD>` → `{daily:[], weekly:[], monthly:[], totals:{}}`；每行含 `period`（daily=`YYYY-MM-DD`、weekly=周一日期、monthly=`YYYY-MM`）、`totalTokens`、`totalCost`、`outputTokens`，`--by-agent` 时另有 `agents:[{agent, totalTokens, totalCost, ...}]` 和 `metadata.agents`
- blocks：`blocks --json --active` → `{blocks:[{isActive, startTime, endTime, totalTokens, costUSD, projection:{totalTokens, totalCost, remainingMinutes}, burnRate}]}`；blocks 已跨 agent 聚合（实测含 gpt-6.1-sol、grok-4.7-build 等）；`--token-limit max` 不给 JSON 增加 tokenLimit 字段，进度条基准改用 `projection.totalTokens`
- 本机实际有数据的 agent（ccusage 检测）：antigravity、claude、codex、grok、hermes、zcode 共 6 个。目录核实：`~/.claude/projects`、`~/.codex/sessions` 有会话；`~/.gemini` 存在但 `tmp/` 为空（Gemini 无数据）；`~/.factory`（Droid）只有 settings.json；antigravity 数据在 `~/.gemini/antigravity`，hermes、zcode 由 ccusage 自行发现。卡片按检测到的 agent 动态出列，不写死三家
- Windows 调用：`subprocess.run` shell=False + `shutil.which('npx.cmd')`（node v26，实测 rc=0）；全量加载一次约 20-60s（本机月量 54 亿 token），生成卡片共跑 daily、blocks 两条命令
- `usage_card.py --json <path>` 接受合并 dump：`{"daily":[...], "weekly":[...], "monthly":[...], "blocks":[...]}`，四个键任选，缺的板块省略；`--demo` 强制内嵌 sample（等价于 ccusage 不可用时的自动兜底，两种卡面都带 DEMO 角标）。样例 dump 在 `out/usage-dump.json`；实测 PNG：`out/usage.png`（真实数据）、`out/usage-demo.png`

## lane 划分

- leader（本会话）：studio/server.py、studio/index.html、集成、端到端验证
- usage-card lane：usage_card.py + cards/usage.html 模板 + ccusage 考证
- opensource lane（低优先级，独立交付）：docs/opensource/ 双语文档
- phase 2（未开工）：圈注→magpie LLM 改版式

## 状态（2026-10-16 20:30，第二轮）

**晚间第二轮全部完成：**

- **Studio v2 UI**（用户驱动重构）：Header 功能区 / 左侧卡片列表侧栏（拖拽调宽）/ 双列内容区（左预览右代码，列间拖拽分宽，交换按钮按用户要求移除）/ 状态栏。实时预览（停止输入 800ms 自动渲染，可关）
- **带壳预览**：CSS 画的 Oasis 壳——竖屏右厚边（翻页键侧）、横屏底部 34px doc+两键凹槽+圆点；Dark=暖石墨铝、Light=银色铝
- **「纸感工作台」主题**（impeccable 流程，用户选定方向）：衬线标题（Georgia）、墨线分隔、铜棕强调（#8a5a2e/#c98f4e）、暖纸面板；滚动条/选区/焦点圈全部主题化；detect 三条 warning 处理（间距节奏已修，两条判为误报/有物理依据）
- **方向**：默认 landscape（用户要求）；方向切换同步壳体与按钮态
- **用量卡 v2**：衬线排版（Georgia old-style 数字）、横屏两列布局（左：今日+周月 / 右：窗口+CLI 表）、`--orientation` 参数；竖屏版同步更新；已推真机（rotate=3 横屏）
- **第三期用量卡自动刷新**：`/api/usage/refresh`（取数→渲染横屏→推内容池，单飞锁）；Header「用量卡→Kindle」按钮
- **圈注改走本地 Agent**（用户简化决策）：页面只圈选+写要求，POST /api/agent-task 落单（studio/agent_tasks/*.json），本地 Claude 会话 GET ?claim=1 领单、POST /api/agent-result 回填；页面 3s 轮询拉结果。/api/ai-edit（直连 magpie）保留为备选
- **托盘应用 studio/tray.py**（pystray）：右下角常驻，菜单=打开工作台/Kindle 恢复正常模式/Kindle 看板模式/退出；同进程 HTTP server；桌面快捷方式「Kindle Studio.lnk」（pythonw 静默启动）
- **Kindle 模式脚本**（设备侧）：normal-mode.sh（恢复 UI 框架/触摸/亮度）、dashboard-mode.sh（独占看板）；用户报的"后台跑时无法操作 Kindle"即独占模式所致，托盘一键切换
- **screenshot.py**：帧缓冲截图（竖屏直接读、横屏 crop(0,0,1680,1264)+ROTATE_90，rotate=3 实测定案）

**坑**（新）：批量替换主题色时误伤了 :root 定义块（自引用导致全透明）——已修；批量替换后必须检查定义块本身。ash 无 local 作用域：apply_orientation 的 cur 曾覆盖主循环 cur 导致 changed 恒 1——设备 shell 函数变量不得与主循环重名。

**坑（追加，2026-10-16 晚 3，最终定案）**：上条"JBM 在前"的方案是错的——Chrome 对 JBM 在前的字体栈，中文字符会跳过栈里的思源宋体直接落到 SimSun（隔离实验实证：直接写 'Noto Serif SC' 正常，JBM 在前就跳过）。定案方案反转：**思源宋体在前**，数字/英文用 latin_wrap() 正则包 .num span（span 内只有纯数字/英文，无回退问题；万/亿必须留在 span 外）。混排文字 font-weight:500 补偿灰度量化的视觉变细。壳拖拽：fitDevice 必须在拖动 mousemove 中实时调用（mouseup 可能因拖出窗口丢失）。

**坑（追加，2026-10-16 晚 2）**：中英混排字体不要用 span 手工包数字——span 的字体栈 JBM+monospace 会让 span 内的"万/亿"回落到系统等宽 CJK，和 span 外的思源宋体同字不同形。正确做法：混排元素字体栈 JBM 在前，浏览器按字符自动分配（数字/英文→JBM，中文→思源宋体）。壳与图同步缩放：CSS aspect-ratio+flex+max 链在极端比例下循环依赖，改 JS fitDevice() 显式算 px；图用 object-fit:contain 兜底永不裁切。

**待办**：托盘开机自启（用户未确认要不要）；screenshot.py 内的 landscape 分支修正为最终验证过的 decode；usage 卡定时器（现手动按钮触发，daemon 侧小时级自动刷新未接）

- studio 核心：**完成并验证**。/api/render（产物与 render.py 直跑逐字节一致）、/api/push（真机 rc=0）、/api/cards、/api/card、/api/usage（现场跑 ccusage，3.5KB HTML）；Playwright 真实 UI 操作验证，console 0 errors，截图 out/studio-ui.png。修掉的 bug：Windows PIL 惰性句柄锁 raw.png（WinError 32）、favicon 404、AI 完成态文案被预览刷新覆盖
- usage-card lane：**完成**。usage_card.py 三种数据源模式（live/--json/--demo）各跑通；ccusage 20.0.34 考证见上方小节；真实用量卡已推上真机（out/usage.png：今日 1.78 亿 tokens/$43.56，6 个 CLI 分列，5h 窗口 87%）；本机有数据的 CLI：antigravity/claude/codex/grok/hermes/zcode，Gemini 目录存在但无会话数据
- phase 2 圈注→AI：**完成并验证**。/api/ai-edit 接 magpie 网关（默认 group/auto-claude-sonnet-5-5，STUDIO_AI_MODEL 可覆盖）；UI 圈注模式（预览上拖拽画框，多框+一句要求）→ AI 重写 HTML → 编辑器替换+自动预览+可还原。端到端验证：curl 层 .rule 6px→2px #bbb 正确；UI 层拖拽圈标题→"字号加大20%"→ h1 92px→110px 正确
- opensource lane：**完成**。docs/opensource/ 9 文件（README/JAILBREAK/SETUP 各中英 + INDEX），含踩坑实录、17 条未验证项清单；开源前待用户处理：AGENTS.md 序列号打码、cmds/work.sh 内嵌公钥、vendor 二进制再分发许可
- 未做：用量卡定时自动刷新（第三期）

## 决策记录

- 2026-10-16 网页方案替代桌面 GUI（浏览器即 GUI 框架，herdr 所有 agent 可共用）
- 2026-10-16 预览零偏差：预览图 = render.py 真实产物，不做浏览器仿真
- 2026-10-16 LLM 接 magpie 网关（本地可信网关，无需 key），不引开源 agent 框架
- 2026-10-16 字体双轨（用户定案）：本机自用 Anthropic Sans，开源/上传层一律 Inter。落地：npm 包 `anthropic-fonts@1.1.0` 实为单个可变字体（wght 300-800 + opsz 16-48）按字重复制，woff2 转 TTF 后改名 family「Anthropic Sans」装进 Windows 用户字体（%LOCALAPPDATA%\Microsoft\Windows\Fonts + HKCU 注册表），**不进仓库**；Inter 4.1 静态 TTF 同法安装，woff2 四字重进 `studio/vendor/fonts/`（OFL 可分发）。栈：UI 与卡片标题 `"Anthropic Sans","Inter",sans-serif`，数字仍 JBM，中文仍思源（serif-first + latin_wrap 那套不变）。验证：playwright 量宽 Anthropic 499.86 / Inter 505.89 / Arial 499.58 px 互不相同（命中真实字体，非回退）；卡片与 Studio 深/浅两主题截图 out/studio-font-*.png；新卡已推真机。坑：python -I 会禁用用户 site-packages（fontTools 装在 --user 位置时 -I 直接 ImportError，脚本里手动 sys.path.insert 解决）；server /vendor 补了 woff2 等 MIME。
