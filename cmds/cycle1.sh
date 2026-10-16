#!/bin/sh
# Cycle 1: probe FBInk reality, install KOReader, then draw the first card last.
Q=/mnt/us/qoder
FB=/mnt/us/libkh/bin/fbink
L=$Q/cycle1.log

{
  echo "=== cycle1 start $(date)"
  echo "--- agentd alive?"; ps | grep '[a]gentd' || echo "agentd NOT running"

  echo "--- fbink env"
  eval "$($FB -e 2>/dev/null)"
  env | grep '^FBINK' | sort

  echo "--- eips info"; /usr/sbin/eips -i 2>&1

  echo "--- kpm install koreader"
  sh /var/local/kmc/sbin/kpm.sh install koreader 2>&1
  echo "kpm rc=$?"
  echo "--- koreader present?"; ls -la /mnt/us/koreader 2>&1 | head -10

  echo "--- draw card attempt 1 (GC16 + flash)"
  $FB -q -c
  $FB -q -W GC16 -f -g "file=$Q/card.png" 2>&1
  rc1=$?
  echo "attempt1 rc=$rc1"
  if [ $rc1 -ne 0 ]; then
    echo "--- draw card attempt 2 (default waveform)"
    $FB -q -f -g "file=$Q/card.png" 2>&1
    echo "attempt2 rc=$?"
  fi

  echo "=== cycle1 end $(date)"
} > $L 2>&1

exit 0
