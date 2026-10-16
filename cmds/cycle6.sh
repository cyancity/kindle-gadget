#!/bin/sh
# Cycle 6: open inbound 23/2222 in the Kindle firewall, restart telnetd,
# and print the result on the e-ink screen so the human can read it back.
Q=/mnt/us/qoder
L=$Q/cycle6.log
E=/usr/sbin/eips
IPT=/usr/sbin/iptables

{
  echo "=== cycle6 $(date)"
  /usr/bin/lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>&1

  IP=$(ifconfig wlan0 | grep 'inet addr' | cut -d' ' -f2 | cut -d: -f2)
  [ -n "$IP" ] || IP=$(ifconfig wlan0 | awk '/inet addr/{print $2}' | cut -d: -f2)
  echo "wlan0 IP = ${IP:-UNKNOWN}"

  echo "--- iptables before"; $IPT -S 2>&1 | head -25
  $IPT -I INPUT -i wlan0 -p tcp --dport 23 -j ACCEPT 2>&1
  $IPT -I INPUT -i wlan0 -p tcp --dport 2222 -j ACCEPT 2>&1
  $IPT -I INPUT -p tcp --dport 23 -j ACCEPT 2>&1
  echo "--- iptables after"; $IPT -S INPUT 2>&1 | head -12
  POL=$($IPT -L INPUT -n 2>&1 | head -1)
  echo "--- INPUT header: $POL"

  killall telnetd 2>&1
  sleep 1
  telnetd -l /bin/sh 2>&1
  sleep 2
  echo "--- listeners"; netstat -ltn 2>&1 | grep -E ':23|:2222'
  echo "--- telnetd proc"; ps -w | grep '[t]elnetd'

  # keep the screen awake for ~40 min in the background
  setsid sh -c 'i=0; while [ $i -lt 40 ]; do /usr/bin/lipc-set-prop com.lab126.powerd preventScreenSaver 1 >/dev/null 2>&1; sleep 60; i=$((i+1)); done' >/dev/null 2>&1 &

  echo "=== end $(date)"
} > $L 2>&1

IP=$(grep -m1 'wlan0 IP' $L 2>/dev/null | cut -d= -f2 | tr -d ' ')
$E -c
$E 1 1 "QODER DEV SESSION"
$E 3 1 "IP     = ${IP:-unknown}"
$E 5 1 "port   = 23 (telnet)"
$E 7 1 "firewall = opened 23/2222"
$E 9 1 "read the IP above and tell the agent"
exit 0
