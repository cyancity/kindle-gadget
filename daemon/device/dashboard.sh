#!/bin/sh
# kindle-gadget 看板 daemon (busybox ash)
# 周期把 current.png 刷上屏。MODE=ac 插电常驻轮询 / MODE=battery 休眠+RTC唤醒。
# 约定: /mnt/us/qoder/daemon/{current.png, meta(可选), config, daemon.log, daemon.pid, .lock}

DIR=/mnt/us/qoder/daemon
FBINK=/mnt/us/libkh/bin/fbink
PNG="$DIR/current.png"
LOG="$DIR/daemon.log"
PIDF="$DIR/daemon.pid"
LOCK="$DIR/.lock"
LOG_MAX=204800
LOG_KEEP=102400
RTC_ALARM=/sys/class/rtc/rtc0/wakealarm
ROTATE_SYS=/sys/class/graphics/fb0/rotate
ALLOWED_WF=' A2 DU GL16 GC16 GC16_FAST GL16_FAST REAGL REAGLD GCK16 GLKW16 GCC16 GLRC16 '
# 方向 → fb rotate 值（真机验证：rotate=1 不花屏但相对产品摆放差 180°，用户确认用 3）
ROTATE_PORTRAIT=0
ROTATE_LANDSCAPE=3

cd "$DIR" || exit 1

# ---------- 单实例 ----------
if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK"
  if ! flock -n -x 9 2>/dev/null; then
    echo "$(date '+%F %T') another instance holds $LOCK, exit" >> "$LOG"
    exit 1
  fi
fi
echo $$ > "$PIDF"

# ---------- 工具 ----------
log() {
  echo "$(date '+%F %T') $*" >> "$LOG"
  sz=$(stat -c %s "$LOG" 2>/dev/null || echo 0)
  if [ "$sz" -gt "$LOG_MAX" ]; then
    tail -c $LOG_KEEP "$LOG" > "$LOG.t" 2>/dev/null && mv -f "$LOG.t" "$LOG"
  fi
}

cleanup() {
  log "daemon stop (signal), releasing preventScreenSaver"
  [ "$MODE" = "ac" ] && lipc-set-prop -i com.lab126.powerd preventScreenSaver 0 >/dev/null 2>&1
  rm -f "$PIDF"
  trap - TERM INT
  exit 0
}
trap cleanup TERM INT

meta_get() {
  [ -f "$DIR/meta" ] || return 0
  sed -n "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*//p" "$DIR/meta" | head -n 1 | tr -d '\r'
}
meta_set() {
  touch "$DIR/meta"
  if grep -q "^[[:space:]]*$1[[:space:]]*=" "$DIR/meta"; then
    sed -i "s/^[[:space:]]*$1[[:space:]]*=.*/$1=$2/" "$DIR/meta"
  else
    echo "$1=$2" >> "$DIR/meta"
  fi
}

load_config() {
  MODE=ac; INTERVAL=60; FULL_EVERY=6; REDRAW_UNCHANGED=1; AWAKE_GRACE=20
  [ -f "$DIR/config" ] && . "$DIR/config" 2>/dev/null
  case "$MODE" in ac|battery) ;; *) MODE=ac ;; esac
  [ "$INTERVAL" -ge 5 ] 2>/dev/null || INTERVAL=60
  [ "$FULL_EVERY" -ge 1 ] 2>/dev/null || FULL_EVERY=6
  [ "$REDRAW_UNCHANGED" = "0" ] || REDRAW_UNCHANGED=1
  [ "$AWAKE_GRACE" -ge 5 ] 2>/dev/null || AWAKE_GRACE=20
}

md5() { md5sum "$1" 2>/dev/null | cut -d' ' -f1; }

# draw <waveform> <flash 0|1>
draw() {
  cp -f "$PNG" "$DIR/draw.png" 2>/dev/null || return 2
  if [ "$2" = "1" ]; then
    "$FBINK" -q -W "$1" -f -g "file=$DIR/draw.png"
  else
    "$FBINK" -q -W "$1" -g "file=$DIR/draw.png"
  fi
}

# 按方向切 fb 旋转；返回 1 表示切过（调用方需全刷一次）
# 注意：ash 无 local，内部变量不要与主循环的 cur/last_hash 重名
apply_orientation() {
  want=$ROTATE_PORTRAIT
  [ "$1" = "landscape" ] && want=$ROTATE_LANDSCAPE
  cur_rot=$(cat "$ROTATE_SYS" 2>/dev/null || echo 0)
  if [ "$cur_rot" != "$want" ]; then
    echo "$want" > "$ROTATE_SYS" 2>/dev/null
    return 1
  fi
  return 0
}

# ---------- 主循环 ----------
load_config
log "daemon start pid=$$ mode=$MODE interval=${INTERVAL}s full_every=$FULL_EVERY redraw_unchanged=$REDRAW_UNCHANGED"

if [ "$MODE" = "ac" ]; then
  if lipc-set-prop -i com.lab126.powerd preventScreenSaver 1 >/dev/null 2>&1; then
    log "preventScreenSaver=1 (ac mode)"
  else
    log "WARN: preventScreenSaver set failed, 设备可能自动休眠"
  fi
fi

count=0
last_hash=none
last_orient=unknown
while :; do
  load_config   # 每轮重读，改 config 不用重启

  force=$(meta_get force_full)
  wfmeta=$(meta_get waveform)
  orient=$(meta_get orientation)
  [ "$orient" = "landscape" ] || orient="portrait"
  cur=$(md5 "$PNG")
  if [ "$cur" = "$last_hash" ] && [ "$orient" = "$last_orient" ]; then changed=0; else changed=1; fi

  full=0
  if [ "$count" -eq 0 ]; then
    full=1                                   # 首刷全刷，对齐底色
  elif [ "$force" = "1" ]; then
    full=1; meta_set force_full 0
  elif [ $(( (count + 1) % FULL_EVERY )) -eq 0 ]; then
    full=1                                   # 每 FULL_EVERY 轮插一次全刷
  fi

  # 方向变化：切旋转并强制全刷
  if ! apply_orientation "$orient"; then
    full=1
    log "orientation -> $orient (fb rotate switched), force full refresh"
  fi

  wf=GL16
  [ "$full" = "1" ] && wf=GC16
  if [ "$full" = "0" ] && [ -n "$wfmeta" ]; then
    case "$ALLOWED_WF" in *" $wfmeta "*) wf=$wfmeta ;; esac
  fi

  if [ "$changed" = "1" ] || [ "$REDRAW_UNCHANGED" = "1" ] || [ "$full" = "1" ]; then
    if draw "$wf" "$full"; then
      count=$((count + 1))
      last_hash=$cur
      last_orient=$orient
      bat=$(gasgauge-info -c 2>/dev/null)
      chg=$(lipc-get-prop -i com.lab126.powerd isCharging 2>/dev/null)
      log "draw #$count wf=$wf full=$full changed=$changed bat=$bat charging=$chg"
      if [ "$chg" = "0" ]; then
        case "$bat" in
          1[0-5]%|[0-9]%) log "WARN battery low: $bat (ac 模式耗电，建议插电或切 MODE=battery)" ;;
        esac
      fi
    else
      log "draw failed rc=$? (png 缺失或 fbink 出错)，下一轮重试"
    fi
  else
    log "skip (unchanged, full 未到期)"
  fi

  if [ "$MODE" = "ac" ]; then
    n=0
    while [ "$n" -lt "$INTERVAL" ]; do
      sleep 5; n=$((n + 5))
    done
  else
    # battery: 布RTC闹钟 -> suspend-to-RAM，到点内核唤醒，本进程从RAM继续
    if echo $(( $(cat /sys/class/rtc/rtc0/since_epoch 2>/dev/null) + INTERVAL )) > "$RTC_ALARM" 2>/dev/null; then
      log "suspend -> mem, ${INTERVAL}s 后 rtc 唤醒"
      echo mem > /sys/power/state
      sleep 2
      log "wakeup from mem, 驻留 ${AWAKE_GRACE}s 等 WiFi/管理通道"
      n=0
      while [ "$n" -lt "$AWAKE_GRACE" ]; do
        sleep 5; n=$((n + 5))
      done
    else
      log "WARN: arm rtc failed, 退化为 sleep"
      sleep "$INTERVAL"
    fi
  fi
done
