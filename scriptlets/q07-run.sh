#!/bin/sh
# Name: Qoder Run 07
# Author: Qoder agent
# DontUseFBInk
Q=/mnt/us/qoder
rm -f $Q/cycle7.log
/usr/bin/lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>&1
setsid sh $Q/work.sh >/dev/null 2>&1 &
/usr/sbin/eips -c
/usr/sbin/eips 2 1 "RUN 07 STARTED"
/usr/sbin/eips 4 1 "NOW COUNT TO 10 AND"
/usr/sbin/eips 5 1 "PLUG THE USB CABLE IN"
/usr/sbin/eips 7 1 "then wait 20 more seconds"
exit 0
