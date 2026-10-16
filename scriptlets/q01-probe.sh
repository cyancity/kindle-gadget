#!/bin/sh
# Name: Qoder Probe 01
# Author: Qoder agent

OUT=/mnt/us/qoder
LOG=$OUT/probe.txt
mkdir -p $OUT

{
  echo "=== marker: probe start $(date)"

  echo "--- id"; id
  echo "--- uname"; uname -a
  echo "--- /etc/version"; cat /etc/version 2>&1
  echo "--- meminfo"; grep -iE 'MemTotal|MemFree|MemAvailable' /proc/meminfo 2>&1
  echo "--- cpu"; grep -m2 -iE 'model name|Processor|BogoMIPS' /proc/cpuinfo 2>&1
  echo "--- PATH"; echo "$PATH"

  echo "--- ls /mnt/us"; ls -la /mnt/us 2>&1
  echo "--- ls /mnt/us/libkh"; ls -laR /mnt/us/libkh 2>&1 | head -40
  echo "--- find kpm"; find /mnt/us /usr/bin /usr/sbin /var/local -maxdepth 3 -iname '*kpm*' 2>/dev/null | head -20
  echo "--- find sh_integration"; find /mnt/us /var/local -maxdepth 4 -iname '*integration*' -o -maxdepth 4 -iname '*.sh' 2>/dev/null | head -30

  echo "--- command probe"
  for c in kpm eips fbink lipc-set-prop lipc-get-prop python python2 perl lua luajit dropbearkey dropbear sshd telnetd nc wget curl sqlite3 iptables ip ifconfig initctl launchkoreader; do
    p=$(command -v $c 2>/dev/null)
    echo "$c -> ${p:-MISSING}"
  done

  echo "--- fbink version"; /mnt/us/libkh/bin/fbink --version 2>&1
  echo "--- fbink help"; /mnt/us/libkh/bin/fbink --help 2>&1 | head -160

  echo "--- net interfaces"; ifconfig -a 2>&1
  echo "--- routes"; cat /proc/net/route 2>&1 | head -10
  echo "--- listening"; netstat -ltnp 2>&1 | head -20

  echo "--- upstart jobs"; initctl list 2>&1 | head -50
  echo "--- procs"; ps 2>&1 | head -40

  echo "--- writable system?"; touch /var/local/qoder_write_test 2>&1 && { echo "/var/local WRITABLE"; rm -f /var/local/qoder_write_test; } || echo "/var/local NOT writable"

  echo "=== marker: probe done $(date)"
} > $LOG 2>&1

if command -v eips >/dev/null 2>&1; then
  eips -c
  eips 0 2 "Qoder probe finished"
  eips 1 2 "log: /mnt/us/qoder/probe.txt"
  eips 3 2 "unplug USB and read it"
fi

exit 0
