#!/usr/bin/env bash
set -e
LOG_FILE="/home/agentuser/logs/th_sync_9router.log"
mkdir -p /home/agentuser/logs

# Rotasi log jika sudah lebih dari 3000 baris agar disk tidak bengkak
if [ -f "$LOG_FILE" ]; then
    LINE_COUNT=$(wc -l < "$LOG_FILE" 2>/dev/null || echo 0)
    if [ "$LINE_COUNT" -gt 3000 ]; then
        tail -n 1000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
    fi
fi

/usr/bin/python3 /home/agentuser/.hermes/profiles/syadagentic/farm/auto_sync_9router.py >> "$LOG_FILE" 2>&1
