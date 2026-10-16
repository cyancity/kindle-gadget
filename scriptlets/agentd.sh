#!/bin/sh
# File-RPC agent: polls /mnt/us/qoder for commands, runs them as root, writes back.
Q=/mnt/us/qoder
while :; do
  if [ -f $Q/STOP ]; then sleep 5; continue; fi
  if [ -f $Q/cmd.go ]; then
    rm -f $Q/cmd.go
    if [ -f $Q/cmd.sh ]; then
      sh $Q/cmd.sh > $Q/cmd.out 2>&1
      echo "__rc=$?" >> $Q/cmd.out
      mv -f $Q/cmd.out $Q/cmd.done
    fi
  fi
  sleep 1
done
