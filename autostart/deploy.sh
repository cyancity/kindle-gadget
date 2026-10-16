#!/usr/bin/env bash
# Deploy kindle-gadget autostart files to the Kindle over SSH.
# Device has no sftp-server/scp: files travel via ssh stdin pipes.
#
# Usage:
#   ./deploy.sh            deploy files + syntax check
#   ./deploy.sh --check    syntax check only (files already deployed)
#   ./deploy.sh --smoke    run autostart.sh once on device (idempotent, equivalent
#                          to the network half of "Qoder Run 08") and show its log
#   ./deploy.sh --status   show current listeners / iptables / log tail
set -euo pipefail

HOST="${KINDLE_HOST:-192.168.1.189}"
PORT=2222
KEY="$HOME/.ssh/kindle"
SSH_OPTS=(-i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=8 -p "$PORT")
DIR="$(cd "$(dirname "$0")" && pwd)"

kssh() { ssh "${SSH_OPTS[@]}" "root@$HOST" "$@"; }

# put <local> <remote> -- strip CR (authoring on Windows) then pipe over ssh
put() {
    tr -d '\r' < "$1" | ssh "${SSH_OPTS[@]}" "root@$HOST" "cat > $2"
}

mode="${1:-deploy}"
case "$mode" in
    --check)
        kssh 'sh -n /mnt/us/qoder/autostart/autostart.sh && sh -n /mnt/us/emergency.sh && echo SYNTAX_OK'
        exit 0 ;;
    --smoke)
        kssh 'sh /mnt/us/qoder/autostart/autostart.sh; echo "--- log:"; tail -30 /mnt/us/qoder/autostart/autostart.log'
        exit 0 ;;
    --status)
        kssh 'netstat -ltn | grep -E ":23 |:2222 "; iptables -L INPUT -n | grep -E "dpt:(23|2222)"; ls -ld /tmp/root; echo "--- autostart.log:"; tail -20 /mnt/us/qoder/autostart/autostart.log 2>/dev/null'
        exit 0 ;;
esac

# --- deploy ---
kssh 'mkdir -p /mnt/us/qoder/autostart/hooks.d'
put "$DIR/autostart.sh" /mnt/us/qoder/autostart/autostart.sh
put "$DIR/emergency.sh" /mnt/us/emergency.sh
kssh 'chmod +x /mnt/us/qoder/autostart/autostart.sh /mnt/us/emergency.sh
      ls -la /mnt/us/qoder/autostart/ /mnt/us/emergency.sh
      sh -n /mnt/us/qoder/autostart/autostart.sh && sh -n /mnt/us/emergency.sh && echo SYNTAX_OK'

echo
echo "Deployed. Next steps:"
echo "  ./deploy.sh --smoke    # run once now, verify idempotence"
echo "  reboot test            # needs leader approval, see DESIGN.md"
