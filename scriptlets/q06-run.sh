#!/bin/sh
# Name: Qoder Run 06
# Author: Qoder agent
# DontUseFBInk
Q=/mnt/us/qoder
rm -f $Q/cycle6.log
/usr/bin/lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>&1
setsid sh $Q/work.sh >/dev/null 2>&1 &
/usr/sbin/eips -c
/usr/sbin/eips 2 1 "RUN 06 STARTED"
/usr/sbin/eips 4 1 "wait 10 seconds"
/usr/sbin/eips 6 1 "then read the IP on screen"
exit 0
