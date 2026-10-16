#!/bin/sh
# Cycle 4: telnetd on all interfaces, keep wifi alive, report current wifi state.
Q=/mnt/us/qoder
L=$Q/cycle4.log
{
  echo "=== cycle4 $(date)"
  echo '--- telnetd before'; ps -w | grep '[t]elnetd'
  killall telnetd 2>&1
  /usr/bin/lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>&1
  /usr/bin/lipc-set-prop com.lab126.cmd wirelessEnable 1 2>&1
  sleep 2
  echo '--- wlan0 now'; ifconfig wlan0 2>&1 | grep -E 'HWaddr|inet addr'
  echo '--- wpa state'; wpa_cli status 2>&1 | head -12
  echo '--- lipc wifid'; /usr/bin/lipc-get-prop com.lab126.wifid cmc 2>&1 | head -c 300
  echo ''
  echo '--- start telnetd 0.0.0.0'
  telnetd -l /bin/sh 2>&1
  sleep 2
  echo '--- listeners'; netstat -ltn 2>&1 | grep ':23'
  echo '--- routes'; netstat -rn 2>&1 | head -8
  echo "=== end $(date)"
} > $L 2>&1
exit 0
