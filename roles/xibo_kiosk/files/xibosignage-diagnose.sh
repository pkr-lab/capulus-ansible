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

section "Warum erreicht multi-user.target so spaet?"
systemd-analyze critical-chain systemd-user-sessions.service 2>&1 | head -20
systemctl list-jobs --no-pager 2>&1 | head -10

section "Startmodus"
systemctl is-enabled xibosignage-xorg.service xibosignage-kiosk.service 2>&1
systemctl status xibosignage-xorg.service xibosignage-kiosk.service --no-pager 2>&1 | grep -E '●|Active:|Main PID' 

section "Kiosk-Zeitstempel (Sekunden seit Kernelstart)"
journalctl -t xibosignage-kiosk -b --no-pager 2>&1 | tail -20

section "Sync"
systemctl status xibosignage-sync.timer --no-pager 2>&1 | head -12
journalctl -u xibosignage-sync.service -b --no-pager 2>&1 | tail -20

section "Cache und Manifest"
ls -l /var/www/xibosignage-slideshow/media 2>&1 | head -30
cat /var/www/xibosignage-slideshow/manifest.js 2>&1
findmnt /mnt/xibosignage-display 2>&1 || echo "NFS aktuell nicht gemountet"

section "Bildschirm (Modus und Seitenverhaeltnis)"
x_user=$(ps -o user= -C Xorg 2>/dev/null | head -1)
x_auth=$(pgrep -a Xorg 2>/dev/null | sed -n 's/.* -auth \([^ ]*\).*/\1/p' | head -1)
kiosk_user=$(systemctl show -p User --value xibosignage-kiosk.service 2>/dev/null)
[ -n "$kiosk_user" ] || kiosk_user=$x_user
if [ -n "$x_auth" ] && [ -r "$x_auth" ]; then
  DISPLAY=:0 XAUTHORITY="$x_auth" xrandr --query 2>&1 | head -20
elif [ -n "$kiosk_user" ]; then
  home=$(getent passwd "$kiosk_user" | cut -d: -f6)
  sudo -u "$kiosk_user" env DISPLAY=:0 XAUTHORITY="$home/.Xauthority" xrandr --query 2>&1 | head -20
fi
echo "erkannt: $(cat /dev/shm/xibosignage-screen 2>/dev/null || echo nichts)"
journalctl -t xibosignage-display -b --no-pager 2>&1 | tail -10
for card in /sys/class/drm/card*-HDMI*; do
  [ -d "$card" ] || continue
  echo "--- $card"
  echo "status: $(cat "$card/status" 2>/dev/null)"
  echo "EDID-Bytes: $(wc -c <"$card/edid" 2>/dev/null)"
  echo "Kernel-Modi (erster Eintrag = bevorzugt):"
  head -8 "$card/modes" 2>/dev/null
done
grep -o 'video=[^ ]*' /proc/cmdline || echo "kein video= in cmdline.txt"
grep -E '^\s*(hdmi_|disable_overscan|overscan_)' /boot/firmware/config.txt /boot/config.txt 2>/dev/null || echo "keine hdmi_*-Zeilen in config.txt"

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
