#!/bin/sh
# 设备侧停止。
DIR=/mnt/us/qoder/daemon
pid=$(cat "$DIR/daemon.pid" 2>/dev/null)
if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
  kill "$pid"
  i=0
  while kill -0 "$pid" 2>/dev/null && [ "$i" -lt 15 ]; do
    sleep 1; i=$((i + 1))
  done
  if kill -0 "$pid" 2>/dev/null; then
    kill -9 "$pid" 2>/dev/null
    rm -f "$DIR/daemon.pid"
    # kill -9 跳过了 trap，这里兜底还原
    lipc-set-prop -i com.lab126.powerd preventScreenSaver 0 >/dev/null 2>&1
  fi
  echo "stopped pid=$pid"
else
  rm -f "$DIR/daemon.pid"
  echo "not running (stale pidfile cleaned)"
fi
