#!/bin/sh
# 设备侧启动（幂等）。已在跑则不动。
DIR=/mnt/us/qoder/daemon
cd "$DIR" || exit 1

pid=$(cat "$DIR/daemon.pid" 2>/dev/null)
if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
  echo "already running pid=$pid"
  exit 0
fi
rm -f "$DIR/daemon.pid"

setsid nohup sh "$DIR/dashboard.sh" >> "$DIR/daemon.log" 2>&1 &
sleep 1
pid=$(cat "$DIR/daemon.pid" 2>/dev/null)
if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
  echo "started pid=$pid (log: $DIR/daemon.log)"
else
  echo "start FAILED, tail log:"
  tail -n 5 "$DIR/daemon.log" 2>/dev/null
  exit 1
fi
