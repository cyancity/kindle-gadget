#!/bin/sh
# Cycle 5: keep awake first, then telnetd on all interfaces, report real wifi state.
Q=/mnt/us/qoder
L=$Q/cycle5.log
{
  echo "=== cycle5 $(date)"
  /usr/bin/lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>&1
  echo "keep-awake set at $(date)"
  killall telnetd 2>&1
  sleep 1
  echo '--- wlan0'; ifconfig wlan0 2>&1 | grep -E 'HWaddr|inet addr'
  echo '--- wpa'; wpa_cli status 2>&1 | head -10
  echo '--- start telnetd 0.0.0.0'
  telnetd -l /bin/sh 2>&1
  sleep 2
  echo '--- listeners'; netstat -ltn 2>&1 | grep ':23'
  echo '--- ping gateway'; ping -c 2 -W 2 192.168.1.1 2>&1 | tail -3
  echo "=== end $(date)"
} > $L 2>&1
exit 0
