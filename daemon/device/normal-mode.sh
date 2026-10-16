#!/bin/sh
# 恢复 Kindle 正常系统：重启 UI 框架、释放防休眠、恢复竖屏。
# 用完设备回归正常触摸/首页/亮度；想再进看板模式跑 dashboard-mode.sh 或等 daemon 下一轮。
lipc-set-prop -i com.lab126.powerd preventScreenSaver 0 2>/dev/null
initctl start framework 2>/dev/null
initctl start lab126_gui 2>/dev/null
echo 0 > /sys/class/graphics/fb0/rotate 2>/dev/null
echo "normal mode restored"
