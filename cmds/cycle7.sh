#!/bin/sh
# Cycle 7: switch the USB port from mass-storage to network (RNDIS gadget),
# bring up usb0 and let the already-running telnetd serve it.
Q=/mnt/us/qoder
L=$Q/cycle7.log
E=/usr/sbin/eips

{
  echo "=== cycle7 $(date)"
  /usr/bin/lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>&1
  echo "--- waiting 25s for the cable to be plugged back in"
  sleep 25

  echo "--- switching volumd to network mode"
  /usr/bin/lipc-set-prop -i com.lab126.volumd useUsbForNetwork 1 2>&1
  /usr/bin/lipc-send-event -r 3 -d 2 com.lab126.hal usbUnconfigured 2>&1
  /usr/bin/lipc-send-event -r 3 -d 2 com.lab126.hal usbPlugOut 2>&1

  i=0
  while [ ! -e /sys/class/net/usb0 ] && [ $i -lt 25 ]; do sleep 1; i=$((i+1)); done
  echo "--- usb0 appeared after ${i}s"

  ifconfig usb0 192.168.15.244 netmask 255.255.255.0 up 2>&1
  echo "--- usb0 state"; ifconfig usb0 2>&1

  killall telnetd 2>&1
  sleep 1
  telnetd -l /bin/sh 2>&1
  sleep 2
  echo "--- listeners"; netstat -ltn 2>&1 | grep ':23'
  echo "--- iptables usb0"; /usr/sbin/iptables -S INPUT 2>&1 | grep -i usb0
  echo "--- routes"; ifconfig -a 2>&1 | grep -E '^[a-z]'
  echo "=== end $(date)"
} > $L 2>&1

$E -c
$E 2 1 "USB NETWORK MODE"
$E 4 1 "device 192.168.15.244"
$E 6 1 "host    192.168.15.201"
$E 8 1 "port 23 open on usb0"
exit 0
