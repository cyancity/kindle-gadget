#!/bin/sh
# 书架 scriptlet: 点书拉起看板 daemon（60 秒超时内启动即返回，daemon 已 setsid 脱离）
cd /mnt/us/qoder/daemon || exit 1
sh start.sh
echo "qoder daemon: $(cat daemon.pid 2>/dev/null || echo 'start failed')"
