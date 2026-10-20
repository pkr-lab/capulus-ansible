#!/usr/bin/env bash
set -u

section() {
  printf '\n===== %s =====\n' "$1"
}

section "Boot-Zeit"
systemd-analyze 2>&1
systemd-analyze critical-chain 2>&1 | head -30

section "Langsamste Units (Top 20)"
systemd-analyze blame 2>&1 | head -20

section "Standard-Target und Display-Manager"
systemctl get-default
systemctl is-enabled lightdm 2>&1
systemctl is-active lightdm 2>&1

section "Kiosk-Zeitstempel (Sekunden seit Kernelstart)"
journalctl -t xibosignage-kiosk -b --no-pager 2>&1 | tail -20

section "Sync"
systemctl status xibosignage-sync.timer --no-pager 2>&1 | head -12
journalctl -u xibosignage-sync.service -b --no-pager 2>&1 | tail -20

section "Cache und Manifest"
ls -l /var/www/xibosignage-slideshow/media 2>&1 | head -30
cat /var/www/xibosignage-slideshow/manifest.js 2>&1
findmnt /mnt/xibosignage-display 2>&1 || echo "NFS aktuell nicht gemountet"

section "Session-Typ und Prozesse"
echo "XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-}"
pgrep -a Xorg 2>&1 || echo "kein Xorg-Prozess"
pgrep -a unclutter 2>&1 || echo "kein unclutter-Prozess"
pgrep -af 'chromium.*--kiosk' 2>&1 | head -3 | cut -c1-200

section "Hardwarebeschleunigung"
ls -l /dev/dri 2>&1
grep -E '^\s*(dtoverlay=vc4|gpu_mem|dtoverlay=disable)' /boot/firmware/config.txt /boot/config.txt 2>/dev/null
command -v vcgencmd >/dev/null 2>&1 && vcgencmd get_mem gpu
for log in /var/log/Xorg.0.log "$HOME/.local/share/xorg/Xorg.0.log"; do
  [ -r "$log" ] && grep -E 'glamor|modeset|EGL|vc4' "$log" | head -10
done
echo "Chromium: im Kiosk per SSH-Tunnel/Tastatur chrome://gpu oeffnen, 'Compositing' und 'Rasterization' muessen 'Hardware accelerated' zeigen"

section "Aktive Dienste (nicht-kritische Kandidaten)"
systemctl list-units --type=service --state=running --no-legend 2>&1 | awk '{print $1}'
