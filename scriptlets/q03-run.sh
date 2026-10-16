#!/bin/sh
# Name: Qoder Run 03
# Author: Qoder agent
# DontUseFBInk
Q=/mnt/us/qoder
rm -f $Q/cycle2.log
if command -v setsid >/dev/null 2>&1; then
  setsid sh $Q/work.sh >/dev/null 2>&1 &
else
  nohup sh $Q/work.sh >/dev/null 2>&1 &
fi
echo "$(date) work.sh spawned from run03" >> $Q/agentd.log 2>&1
/usr/sbin/eips -c
/usr/sbin/eips 2 1 "CYCLE 03 SPAWNED"
/usr/sbin/eips 4 1 "leave it alone 5 min"
/usr/sbin/eips 6 1 "log: /mnt/us/qoder/cycle2.log"
exit 0
