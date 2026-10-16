#!/bin/sh
# 进/回看板独占模式：停 UI 框架、防休眠、重画当前内容。daemon 仍在跑时无需执行（它自己管刷屏）。
initctl stop lab126_gui 2>/dev/null
initctl stop framework 2>/dev/null
lipc-set-prop -i com.lab126.powerd preventScreenSaver 1 2>/dev/null
/mnt/us/libkh/bin/fbink -q -W GC16 -f -g "file=/mnt/us/qoder/daemon/current.png" 2>/dev/null
echo "dashboard mode active"
