# push.py — 一条命令推卡上屏

给 agent 的调用说明。拿到 HTML 或 PNG 内容后照抄下面的命令即可，不需要了解渲染、SSH、FBInk 细节。

## 一行命令

推 HTML（自动渲染 → 传输 → 全刷上屏）：

    python push.py cards/xxx.html

推 PNG（跳过渲染，直接传输 + 全刷）：

    python push.py out/xxx.png

内容只是小改动、不想黑屏闪一下（局刷 GL16）：

    python push.py cards/xxx.html --partial

只传文件不刷屏（配合 --path 先攒文件）：

    python push.py cards/xxx.html --no-refresh

指定设备侧落点（默认 `/mnt/us/qoder/card.png`）：

    python push.py cards/xxx.html --path /mnt/us/qoder/xxx.png

渲染参数覆盖（仅 HTML 输入有效；默认 1264x1680、16 阶、floyd 抖动）：

    python push.py cards/xxx.html --width 1264 --height 1680 --levels 16 --dither floyd

## 行为说明

- HTML 先经仓库里的 render.py：Chrome headless 截图 → 16 阶灰度 Floyd–Steinberg 抖动，产物在 `out/push-<卡片名>.png`。
- PNG 尺寸不是 1264x1680 时自动等比缩放 + 白底补边再转灰度；尺寸正好则字节原样直传。
- 设备上没有 sftp/scp，用 `cat | ssh` 管道传（密钥 `~/.ssh/kindle`，设备 `192.168.1.189:2222`）。
- 刷屏：全刷 `fbink -q -W GC16 -f`，`--partial` 局刷 `-W gl16`（无黑闪）。
- Git Bash 会改写 `--path` 里以 `/` 开头的参数，push.py 已自动修复，不用特殊处理。
- 卡片建议：白底黑字、1264x1680，避免细小彩色元素（墨水屏只显示 16 阶灰度）。仓库现成例子 `cards/push-test-hello.html`。

## 出错自查

- **连不上 Kindle / 提示检查休眠**：设备大概率睡了或 Wi-Fi 断了。按一下电源键唤醒，确认连着家里 Wi-Fi。本机侧可 `ping $KINDLE_HOST`、`arp -a` 查 `7c-d5-66` 开头的 MAC 还在不在。注意本机开着 Clash TUN 时 ping 不通不代表设备失联，以报错里的 ssh 输出为准。
- **SSH 认证被拒**：检查 `~/.ssh/kindle` 私钥是否存在。设备重启后 dropbear 不会自启，需要人在书架上点 "Qoder Run 08" 恢复网络模式（详见 AGENTS.md）。
- **渲染失败**：报错里带 render.py 的输出，常见原因是 Chrome/Edge 不在默认安装路径。
- **只支持 .html/.htm/.png**：其他扩展名直接拒绝。
- **--path 不能指向 /mnt/us/qoder/daemon/**：那是另一个 agent 的目录。

## 硬约束（对设备）

- 不写 rootfs；不重启设备；不 kill telnetd/dropbear。
- `--path` 放 `/mnt/us/` 下的路径，不要带空格。
