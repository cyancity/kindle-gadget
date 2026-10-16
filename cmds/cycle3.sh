#!/bin/sh
# Cycle 3: temporary LAN-only root channel via busybox telnetd.
Q=/mnt/us/qoder
L=$Q/cycle3.log
{
  echo "=== cycle3 $(date)"
  /usr/bin/lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>&1
  /usr/bin/lipc-set-prop com.lab126.cmd wirelessEnable 1 2>&1
  echo '--- wlan0'; ifconfig wlan0 2>&1 | grep 'inet addr'
  echo '--- start telnetd bound to wlan0'
  telnetd -l /bin/sh -b 192.168.0.100 2>&1 || telnetd -l /bin/sh 2>&1
  sleep 2
  echo '--- listeners'; netstat -ltn 2>&1 | head -20
  echo '--- telnetd proc'; ps | grep '[t]elnetd'
  echo '--- kill stale agentd? (leave it)'; ps | grep '[a]gentd'
  echo "=== end $(date)"
} > $L 2>&1
exit 0
