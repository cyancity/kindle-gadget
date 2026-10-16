#!/bin/sh
# Real work, runs detached from the scriptlet so the 60s unload kill cannot hit it.
Q=/mnt/us/qoder
K=/mnt/us/koreader
L=$Q/cycle2.log

{
  echo "=== cycle2 start $(date)"
  id
  RH=$(grep '^root:' /etc/passwd | cut -d: -f6)
  [ -n "$RH" ] || RH=/root
  echo "--- root home: $RH"
  ls -d /root /var/root 2>&1

  echo "--- kpm install koreader"
  sh /var/local/kmc/sbin/kpm.sh install koreader 2>&1
  echo "kpm rc=$?"
  echo "--- koreader tree"; ls -la $K 2>&1 | head -18
  echo "--- dropbear binaries"; find $K -maxdepth 3 -type f -name 'dropbear*' 2>/dev/null
  echo "--- how koreader launches it"
  grep -n 'dropbear' $K/plugins/SSH.koplugin/main.lua 2>&1 | head -25

  echo "--- keep wifi awake"
  /usr/bin/lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>&1
  /usr/bin/lipc-set-prop com.lab126.cmd wirelessEnable 1 2>&1

  echo "--- authorized_keys"
  mkdir -p $RH/.ssh && chmod 700 $RH/.ssh
  # 把下面一行换成你自己的公钥（PC 上 ssh-keygen 生成的 .pub 文件内容）
  cat > $RH/.ssh/authorized_keys <<'KEYEOF'
ssh-rsa AAAA...REPLACE-WITH-YOUR-OWN-PUBKEY... you@pc
KEYEOF
  chmod 600 $RH/.ssh/authorized_keys
  echo "wrote $RH/.ssh/authorized_keys"

  DB=$(find $K -maxdepth 3 -type f -name 'dropbear' | head -1)
  DK=$(find $K -maxdepth 3 -type f -name 'dropbearkey' | head -1)
  echo "--- dropbear=$DB dropbearkey=$DK"
  if [ -n "$DB" ]; then
    if [ -n "$DK" ]; then
      $DK -t rsa -f $Q/db.rsa 2>&1 | tail -2
      $DB -r $Q/db.rsa -s -p 2222 -B 2>&1 | head -5
    else
      $DB -R -s -p 2222 -B 2>&1 | head -5
    fi
    echo "launch rc=$?"
    sleep 3
    echo "--- listeners"; netstat -ltn 2>&1 | head -18
    echo "--- dropbear proc"; ps | grep -i '[d]ropbear'
  else
    echo "NO dropbear binary - koreader install failed?"
  fi

  echo "--- wlan0"; ifconfig wlan0 2>&1 | grep 'inet addr'
  echo "=== cycle2 end $(date)"
} > $L 2>&1

exit 0
