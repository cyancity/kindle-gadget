#!/bin/sh
# Name: Qoder Run 05
# Author: Qoder agent
# DontUseFBInk
Q=/mnt/us/qoder
rm -f $Q/cycle5.log
/usr/bin/lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>&1
setsid sh $Q/work.sh >/dev/null 2>&1 &
/usr/sbin/eips -c
/usr/sbin/eips 2 1 "RUN 05 STARTED"
/usr/sbin/eips 4 1 "do not touch the device"
/usr/sbin/eips 6 1 "log: qoder/cycle5.log"
exit 0
