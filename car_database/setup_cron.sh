#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# setup_cron.sh — install the daily LeBonCoin car scraper cron
# ─────────────────────────────────────────────────────────────
# Usage:
#   bash setup_cron.sh                      # 07:00 daily, no proxy
#   bash setup_cron.sh --time "30 6"        # 06:30 daily
#   HTTPS_PROXY=http://user:pass@host:port bash setup_cron.sh
#
# NOTE: LeBonCoin blocks datacenter/VPS IPs.
#   On a home machine  → runs without proxy.
#   On a cloud server  → set HTTPS_PROXY to a residential proxy URL.
# ─────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$(command -v python3)"
CRON_TIME="${CRON_TIME:-0 7}"   # default: 07:00 every day

# ── Parse --time argument ─────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --time) CRON_TIME="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# ── Build cron line ───────────────────────────────────────────
PROXY_EXPORT=""
if [[ -n "${HTTPS_PROXY:-}" ]]; then
    PROXY_EXPORT="HTTPS_PROXY=${HTTPS_PROXY} "
fi

LOG_FILE="${SCRIPT_DIR}/scraper.log"
CRON_CMD="${CRON_TIME} * * * cd ${SCRIPT_DIR} && ${PROXY_EXPORT}${PYTHON} daily_scraper.py >> ${LOG_FILE} 2>&1"

# ── Install ───────────────────────────────────────────────────
echo "Installing cron job:"
echo "  ${CRON_CMD}"
echo ""

(crontab -l 2>/dev/null | grep -v "daily_scraper.py"; echo "${CRON_CMD}") | crontab -

echo "Done. Current crontab:"
crontab -l | grep "daily_scraper"
