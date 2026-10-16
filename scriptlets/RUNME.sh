#!/bin/sh
# Qoder bootstrap: one-shot probe, then start the file-RPC agent.
Q=/mnt/us/qoder
mkdir -p $Q
LOG=$Q/probe.txt
FB=/mnt/us/libkh/bin/fbink

{
  echo "=== probe start $(date)"
  echo "--- id"; id
  echo "--- uname"; uname -a
  echo "--- /etc/version"; cat /etc/version 2>&1
  echo "--- PATH=$PATH"
  echo "--- mem"; grep -E 'MemTotal|MemFree|MemAvailable' /proc/meminfo 2>&1
  echo "--- jb flags"; ls -la /MNTUS_EXEC /PRE_GM_DEBUGGING_FEATURES_ENABLED__REMOVE_AT_GMC 2>&1
  echo "--- ls /mnt/us"; ls -la /mnt/us 2>&1
  echo "--- kmc/kpm"; ls -la /var/local/kmc 2>&1 | head -25; command -v kpm 2>&1
  echo "--- sh_integration"; ls -la /var/local/kmc/bin 2>&1 | head -15
  echo "--- extensions"; ls -la /mnt/us/extensions /mnt/us/mrpackages /mnt/us/bin 2>&1
  echo "--- net"; ifconfig -a 2>&1
  echo "--- routes"; cat /proc/net/route 2>&1 | head -6
  echo "--- listening"; netstat -ltn 2>&1 | head -15
  echo "--- commands"
  for c in eips fbink lipc-set-prop lipc-get-prop lipc-send-event telnetd dropbear sshd nc curl wget python python2 lua luajit setsid nohup initctl launchkoreader; do
    printf '  %s = %s\n' "$c" "$(command -v $c 2>/dev/null || echo MISSING)"
  done
  echo "--- fbink"; $FB --version 2>&1
  echo "--- fbink env"
  eval "$($FB -e 2>/dev/null)"
  echo "  screen=${FBINK_SCREENWIDTH}x${FBINK_SCREENHEIGHT} rot=${FBINK_SCREEN_ROTATION} maxgray=${FBINK_SCREEN_MAXGRAYLEVELS} px=${FBINK_SCREEN_XDPI}x${FBINK_SCREEN_YDPI}"
  echo "--- ota block"; ls -la /usr/bin/otaupd /usr/bin/otaupd.bck /usr/bin/otav3 /usr/bin/otav3.bck 2>&1
  echo "--- upstart"; initctl list 2>&1 | head -40
  echo "=== probe end $(date)"
} > $LOG 2>&1

chmod +x $Q/agentd.sh 2>/dev/null
echo "$(date) starting agentd" >> $Q/agentd.log 2>&1
if command -v setsid >/dev/null 2>&1; then
  setsid sh $Q/agentd.sh >> $Q/agentd.log 2>&1 &
else
  nohup sh $Q/agentd.sh >> $Q/agentd.log 2>&1 &
fi
exit 0
