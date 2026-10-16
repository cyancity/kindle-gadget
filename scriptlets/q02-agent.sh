#!/bin/sh
# Name: Qoder Agent 02
# Author: Qoder agent
# DontUseFBInk
Q=/mnt/us/qoder
mkdir -p $Q
rm -f $Q/cmd.done $Q/cmd.go $Q/STOP

if ps | grep -q "[a]gentd.sh"; then
  echo "$(date) agentd already running" >> $Q/agentd.log
else
  chmod +x $Q/agentd.sh
  if command -v setsid >/dev/null 2>&1; then
    setsid sh $Q/agentd.sh >> $Q/agentd.log 2>&1 &
  else
    nohup sh $Q/agentd.sh >> $Q/agentd.log 2>&1 &
  fi
  echo "$(date) agentd started pid=$!" >> $Q/agentd.log
fi

sleep 1
if command -v eips >/dev/null 2>&1; then
  eips -c
  eips 2 1 "QODER AGENT RUNNING"
  eips 4 1 "rpc dir: $Q"
  eips 6 1 "stop: touch $Q/STOP"
  eips 8 1 "$(ps | grep '[a]gentd.sh')"
fi
exit 0
