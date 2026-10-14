#!/bin/bash
# Watchdog: ONLY restart if service is actually down. Never kill running browsers.
while true; do
    if ! systemctl is-active --quiet redmess-thfarm.service; then
        echo "[!] thfarm down, restarting..." >> /tmp/th_wd.log
        systemctl start redmess-thfarm.service
    fi
    if ! systemctl is-active --quiet redmess-thnotif.service; then
        systemctl start redmess-thnotif.service
    fi
    sleep 45
done
