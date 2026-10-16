#!/bin/sh
# kindle-gadget dev-channel autostart (KOA3, FW 5.18.2, SpiderCat jb.sh v2.2.1)
#
# Boot invocation chain:
#   /etc/upstart/kmc.conf  (SpiderCat upstart job, "start on framework_ready")
#     -> /mnt/us/emergency.sh   (kmc.conf pre-start, runs as root)
#       -> this script
#
# Hard rules: no rootfs writes; return fast (pre-start blocks until we exit);
# idempotent (re-runnable any time). Details: autostart/DESIGN.md in the repo.

BASE=/mnt/us/qoder/autostart
LOG=$BASE/autostart.log

# keep the log bounded (keep last ~16K)
if [ -f "$LOG" ] && [ "$(/usr/bin/wc -c < "$LOG")" -gt 51200 ]; then
    /usr/bin/tail -c 16384 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

log() { echo "[$(/bin/date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

log "=== autostart invoked (pid $$)"

# --- 1. firewall: allow inbound 23 (telnet) / 2222 (dropbear), no duplicate rules
for PORT in 23 2222; do
    if /usr/sbin/iptables -C INPUT -p tcp --dport $PORT -j ACCEPT 2>/dev/null; then
        log "iptables: dport $PORT already allowed"
    else
        if /usr/sbin/iptables -I INPUT 1 -p tcp --dport $PORT -j ACCEPT 2>>"$LOG"; then
            log "iptables: allowed dport $PORT"
        else
            log "iptables: FAILED to allow dport $PORT"
        fi
    fi
done

# --- 2. telnetd on 0.0.0.0:23 (busybox, root, no auth)
if /bin/netstat -ltn 2>/dev/null | /bin/grep -q ":23 "; then
    log "telnetd: already listening"
else
    if /bin/busybox telnetd -l /bin/sh 2>>"$LOG"; then
        log "telnetd: started"
    else
        log "telnetd: FAILED to start"
    fi
fi

# --- 3. /tmp/root perms: dropbear silently refuses auth if root home is
#        group-writable (stock 2770); 2700 is required (see AGENTS.md)
/bin/chmod 2700 /tmp/root
log "chmod 2700 /tmp/root done"

# --- 4. dropbear on 2222; MUST start with CWD=/mnt/us/koreader
#        (dropbear resolves its paths relative to CWD; AGENTS.md 2026-10-16)
if /bin/netstat -ltn 2>/dev/null | /bin/grep -q ":2222 "; then
    log "dropbear: already listening"
else
    if [ -x /mnt/us/kmc/kpm/packages/koreader/koreader/dropbear ]; then
        ( cd /mnt/us/koreader && /mnt/us/kmc/kpm/packages/koreader/koreader/dropbear -R -s -p 2222 )
        log "dropbear: started"
    else
        log "dropbear: BINARY MISSING (/mnt/us/kmc/kpm/packages/koreader/koreader/dropbear)"
    fi
fi

# --- 5. reserved hook slot: dashboard daemon and friends
#        Drop an executable .sh into $BASE/hooks.d/ and it runs detached here
#        on every boot. Hooks must daemonize themselves or background quickly.
if [ -d "$BASE/hooks.d" ]; then
    for H in "$BASE"/hooks.d/*.sh; do
        if [ -f "$H" ]; then
            log "hook: starting $H"
            /usr/bin/setsid sh "$H" >> "$BASE/hooks.log" 2>&1 &
        fi
    done
fi

log "=== autostart done"
exit 0
